package com.infrawrench.bulkinstances;

import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import java.io.IOException;
import java.util.Arrays;

/**
 * Raw bundle rows of numbers, stored flat: a {@code null} cell is NaN, and each row keeps its length so short
 * rows stay distinguishable from {@code null} cells. Cells past {@code width} are dropped.
 */
final class Rows {
    static final Rows EMPTY = new Rows(1, new double[0], new byte[0]);

    private final int width;
    private final double[] cells;
    private final byte[] lengths;

    private Rows(int width, double[] cells, byte[] lengths) {
        this.width = width;
        this.cells = cells;
        this.lengths = lengths;
    }

    int size() {
        return lengths.length;
    }

    /** How many cells the row has, at most {@code width}. */
    int length(int row) {
        return lengths[row];
    }

    /** The cell, or NaN if it is {@code null} or the row is shorter. */
    double get(int row, int col) {
        return col < lengths[row] ? cells[row * width + col] : Double.NaN;
    }

    /** Reads an array of rows; the parser is on its {@code START_ARRAY}. */
    static Rows parse(JsonParser p, int width) throws IOException {
        expect(p, JsonToken.START_ARRAY);
        double[] cells = new double[16 * width];
        byte[] lengths = new byte[16];
        int rows = 0;
        while (p.nextToken() != JsonToken.END_ARRAY) {
            expect(p, JsonToken.START_ARRAY);
            if (rows == lengths.length) {
                lengths = Arrays.copyOf(lengths, rows * 2);
                cells = Arrays.copyOf(cells, rows * 2 * width);
            }
            int n = 0;
            for (JsonToken t; (t = p.nextToken()) != JsonToken.END_ARRAY; n++) {
                if (n < width) cells[rows * width + n] = number(p, t);
                else p.skipChildren();
            }
            lengths[rows++] = (byte) Math.min(n, width);
        }
        return new Rows(width, Arrays.copyOf(cells, rows * width), Arrays.copyOf(lengths, rows));
    }

    /** The current number, or NaN for {@code null}. */
    static double number(JsonParser p, JsonToken t) throws IOException {
        if (t == JsonToken.VALUE_NULL) return Double.NaN;
        if (t == JsonToken.VALUE_NUMBER_INT || t == JsonToken.VALUE_NUMBER_FLOAT) return p.getDoubleValue();
        throw new JsonParseException(p, "Expected a number or null, got " + t);
    }

    static void expect(JsonParser p, JsonToken t) throws IOException {
        if (p.currentToken() != t) throw new JsonParseException(p, "Expected " + t + ", got " + p.currentToken());
    }
}
