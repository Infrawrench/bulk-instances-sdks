package com.infrawrench.bulkinstances;

/**
 * One instance as the bundle stores it: {@code [attrs, attrChanges, basePrice, onDemand, reserved, createdAt,
 * deletedAt]}, every string an index into {@code compression_table} and {@code null} as NaN.
 */
record RawInstance(
        Rows attrs, Rows attrChanges, double basePrice, Rows onDemand, Rows reserved, double createdAt,
        double deletedAt) {}
