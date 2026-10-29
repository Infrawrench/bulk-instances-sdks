# frozen_string_literal: true

require "fiddle"
require "fiddle/import"

module Infrawrench
  module BulkInstances
    # @api private
    #
    # The few liblzma calls needed to decompress an .xz stream, through Fiddle. liblzma
    # ships with macOS and practically every Linux distribution; this file is only
    # loaded when a bundle has to be downloaded, so cached loads never need it.
    module XZ
      extend Fiddle::Importer

      LIBRARIES = %w[liblzma.so.5 liblzma.5.dylib liblzma.so liblzma.dylib liblzma.dll lzma.dll].freeze

      def self.open_library
        LIBRARIES.each do |name|
          return Fiddle::Handle.new(name)
        rescue Fiddle::DLError
          next
        end
        raise Fiddle::DLError, "liblzma not found (tried #{LIBRARIES.join(", ")}): install xz to download bundles"
      end
      private_class_method :open_library

      dlload open_library

      # lzma_stream, unchanged since liblzma 5.0.
      Stream = struct([
        "const uint8_t *next_in", "size_t avail_in", "uint64_t total_in",
        "uint8_t *next_out", "size_t avail_out", "uint64_t total_out",
        "void *allocator", "void *internal",
        "void *reserved_ptr1", "void *reserved_ptr2", "void *reserved_ptr3", "void *reserved_ptr4",
        "uint64_t seek_pos", "uint64_t reserved_int2", "size_t reserved_int3", "size_t reserved_int4",
        "int reserved_enum1", "int reserved_enum2",
      ])

      extern "int lzma_stream_decoder(void *, uint64_t, uint32_t)"
      extern "int lzma_code(void *, int)"
      extern "void lzma_end(void *)"

      OK = 0
      STREAM_END = 1
      RUN = 0
      FINISH = 3
      CONCATENATED = 0x08
      NO_MEMLIMIT = 2**64 - 1
      BUFFER_SIZE = 1 << 20

      ERRORS = {
        5 => "out of memory", 7 => "not in the .xz format", 8 => "unsupported options",
        9 => "corrupt data", 10 => "truncated data",
      }.freeze

      # Decompresses the .xz data the block writes with +<<+ and returns it as a UTF-8 String.
      def self.decompress
        decoder = Decoder.new
        yield decoder
        decoder.finish
      ensure
        decoder&.close
      end

      # Feeds the input through malloc'd buffers, so liblzma, which runs without the
      # GVL, never points into Ruby memory.
      class Decoder
        def initialize
          @in = Fiddle::Pointer.malloc(BUFFER_SIZE, Fiddle::RUBY_FREE)
          @out = Fiddle::Pointer.malloc(BUFFER_SIZE, Fiddle::RUBY_FREE)
          ptr = Fiddle::Pointer.malloc(Stream.size, Fiddle::RUBY_FREE)
          ptr[0, Stream.size] = "\0" * Stream.size # LZMA_STREAM_INIT
          @stream = Stream.new(ptr)
          check(XZ.lzma_stream_decoder(@stream, NO_MEMLIMIT, CONCATENATED))
          @result = String.new(encoding: Encoding::BINARY)
        end

        def <<(chunk)
          (0...chunk.bytesize).step(BUFFER_SIZE) do |offset|
            piece = chunk.byteslice(offset, BUFFER_SIZE)
            @in[0, piece.bytesize] = piece
            code(piece.bytesize, RUN)
          end
          self
        end

        def finish
          code(0, FINISH)
          @result.force_encoding(Encoding::UTF_8)
        end

        def close
          XZ.lzma_end(@stream) if @stream
          @stream = nil
        end

        private

        def code(size, action)
          @stream.next_in = @in
          @stream.avail_in = size
          loop do
            @stream.next_out = @out
            @stream.avail_out = BUFFER_SIZE
            ret = XZ.lzma_code(@stream, action)
            produced = BUFFER_SIZE - @stream.avail_out
            @result << @out[0, produced] if produced.positive?
            return if ret == STREAM_END
            check(ret)
            # RUN is done once the input is consumed and liblzma had output space to spare.
            # FINISH runs until STREAM_END; liblzma reports truncated input as an error.
            return if action == RUN && @stream.avail_in.zero? && @stream.avail_out.positive?
          end
        end

        def check(ret)
          return if ret == OK

          raise AWSPricingDataError, "Could not decompress the bundle: #{ERRORS.fetch(ret, "liblzma error #{ret}")}."
        end
      end
    end
  end
end
