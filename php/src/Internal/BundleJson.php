<?php

declare(strict_types=1);

namespace Infrawrench\BulkInstances\Internal;

/**
 * Splits a bundle into its small top-level parts, which are decoded, and the rows of each
 * instance, which are left as JSON. Instance rows hold only numbers and `null` (every string
 * is an index into `compression_table`), so the next `"` or `}` always ends an instance.
 *
 * @internal
 */
final class BundleJson
{
    private const WS = " \t\n\r";
    private const ROW_CHARS = "0123456789-+.eE[],nul \t\n\r";
    private const FLAGS = JSON_THROW_ON_ERROR;

    private function __construct()
    {
    }

    /**
     * @return array{array<string, mixed>, array<string, array{int, int}>|null} The decoded top-level members other
     *     than `instances`, and the offset and length of each instance's rows (`null` if `instances` is not an object).
     *
     * @throws \JsonException
     */
    public static function split(string $json): array
    {
        $top = [];
        $spans = null;
        $p = self::skipWs($json, 0);
        self::expect($json, $p, '{');
        $p = self::skipWs($json, $p + 1);
        if (($json[$p] ?? '') === '}') {
            $p++;
        } else {
            while (true) {
                [$key, $p] = self::key($json, $p);
                if ($key === 'instances' && ($json[$p] ?? '') === '{') {
                    [$spans, $p] = self::instances($json, $p);
                    unset($top[$key]);
                } else {
                    $end = self::valueEnd($json, $p);
                    $top[$key] = json_decode(substr($json, $p, $end - $p), true, 512, self::FLAGS);
                    if ($key === 'instances') {
                        $spans = null;
                    }
                    $p = $end;
                }
                $p = self::skipWs($json, $p);
                if (($json[$p] ?? '') !== ',') {
                    break;
                }
                $p = self::skipWs($json, $p + 1);
            }
            self::expect($json, $p, '}');
            $p++;
        }
        if (self::skipWs($json, $p) !== strlen($json)) {
            throw self::error($p);
        }
        return [$top, $spans];
    }

    /**
     * @return array<mixed> The rows of one instance.
     *
     * @throws \JsonException
     */
    public static function decode(string $json, int $offset, int $length): array
    {
        $raw = json_decode(substr($json, $offset, $length), true, 512, self::FLAGS);
        return is_array($raw) ? $raw : throw self::error($offset);
    }

    /**
     * @return array{array<string, array{int, int}>, int}
     *
     * @throws \JsonException
     */
    private static function instances(string $json, int $p): array
    {
        $spans = [];
        $p = self::skipWs($json, $p + 1);
        if (($json[$p] ?? '') === '}') {
            return [$spans, $p + 1];
        }
        while (true) {
            [$key, $start] = self::key($json, $p);
            $stop = $start + strcspn($json, '"}', $start);
            if ($stop >= strlen($json)) {
                throw self::error($start);
            }
            $last = $json[$stop] === '}';
            $end = self::trimWsEnd($json, $start, $stop);
            if (!$last) {
                if ($end === $start || $json[$end - 1] !== ',') {
                    throw self::error($end);
                }
                $end = self::trimWsEnd($json, $start, $end - 1);
            }
            $length = $end - $start;
            if ($length < 2 || $json[$start] !== '[' || $json[$end - 1] !== ']'
                || strspn($json, self::ROW_CHARS, $start, $length) !== $length) {
                throw self::error($start);
            }
            $spans[$key] = [$start, $length];
            if ($last) {
                return [$spans, $stop + 1];
            }
            $p = $stop;
        }
    }

    /**
     * Reads `"key":` and the whitespace after it.
     *
     * @return array{string, int} The key and where its value starts.
     *
     * @throws \JsonException
     */
    private static function key(string $json, int $p): array
    {
        self::expect($json, $p, '"');
        $end = self::stringEnd($json, $p);
        $key = json_decode(substr($json, $p, $end - $p), false, 512, self::FLAGS);
        if (!is_string($key)) {
            throw self::error($p);
        }
        $p = self::skipWs($json, $end);
        self::expect($json, $p, ':');
        return [$key, self::skipWs($json, $p + 1)];
    }

    /** @throws \JsonException */
    private static function valueEnd(string $json, int $p): int
    {
        $c = $json[$p] ?? '';
        if ($c === '"') {
            return self::stringEnd($json, $p);
        }
        if ($c !== '[' && $c !== '{') {
            return $p + strcspn($json, ',}]' . self::WS, $p);
        }
        $depth = 0;
        $n = strlen($json);
        while (true) {
            $p += strcspn($json, '"[]{}', $p);
            if ($p >= $n) {
                throw self::error($p);
            }
            $c = $json[$p];
            if ($c === '"') {
                $p = self::stringEnd($json, $p);
                continue;
            }
            $depth += $c === '[' || $c === '{' ? 1 : -1;
            $p++;
            if ($depth === 0) {
                return $p;
            }
        }
    }

    /**
     * Where the string starting at `$p` ends, after its closing quote.
     *
     * @throws \JsonException
     */
    private static function stringEnd(string $json, int $p): int
    {
        $q = $p + 1;
        while (true) {
            $q = strpos($json, '"', $q);
            if ($q === false) {
                throw self::error($p);
            }
            $backslashes = 0;
            while ($json[$q - 1 - $backslashes] === '\\') {
                $backslashes++;
            }
            $q++;
            if ($backslashes % 2 === 0) {
                return $q;
            }
        }
    }

    private static function skipWs(string $json, int $p): int
    {
        return $p + strspn($json, self::WS, $p);
    }

    private static function trimWsEnd(string $json, int $start, int $end): int
    {
        while ($end > $start && str_contains(self::WS, $json[$end - 1])) {
            $end--;
        }
        return $end;
    }

    /** @throws \JsonException */
    private static function expect(string $json, int $p, string $char): void
    {
        if (($json[$p] ?? '') !== $char) {
            throw self::error($p);
        }
    }

    private static function error(int $offset): \JsonException
    {
        return new \JsonException("Syntax error in the bundle near offset $offset", JSON_ERROR_SYNTAX);
    }
}
