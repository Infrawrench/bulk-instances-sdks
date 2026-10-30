using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.Linq;

namespace Infrawrench.BulkInstances;

/// <summary>A bundle's variant keys, without repeats, and where each one's value is.</summary>
internal sealed class VariantLayout
{
    internal VariantLayout(IReadOnlyList<string> variantKeys)
    {
        Keys = variantKeys.Distinct(StringComparer.Ordinal).ToArray();
        Index = new Dictionary<string, int>(Keys.Length, StringComparer.Ordinal);
        for (var i = 0; i < Keys.Length; i++) Index[Keys[i]] = i;
    }

    internal string[] Keys { get; }

    internal Dictionary<string, int> Index { get; }
}

/// <summary>
/// One variant's fields, keyed by name, in <see cref="AwsPricingData.VariantKeys"/> order. Every variant
/// of a bundle shares its <see cref="VariantLayout"/>. Equal to another with the same keys and values.
/// </summary>
internal sealed class VariantMap : IReadOnlyDictionary<string, string>, IEquatable<VariantMap>
{
    private readonly VariantLayout _layout;
    private readonly string[] _values;

    internal VariantMap(VariantLayout layout, string[] values)
    {
        _layout = layout;
        _values = values;
    }

    public string this[string key] =>
        TryGetValue(key, out var value) ? value : throw new KeyNotFoundException($"The variant has no {key}.");

    public IEnumerable<string> Keys => _layout.Keys;

    public IEnumerable<string> Values => _values;

    public int Count => _values.Length;

    public bool ContainsKey(string key) => _layout.Index.ContainsKey(key);

    public bool TryGetValue(string key, [MaybeNullWhen(false)] out string value)
    {
        if (_layout.Index.TryGetValue(key, out var i))
        {
            value = _values[i];
            return true;
        }
        value = null;
        return false;
    }

    /// <summary>The value of <paramref name="key"/>, or <c>""</c> if the variant has no such field.</summary>
    internal string GetOrEmpty(string key) => TryGetValue(key, out var value) ? value : "";

    public IEnumerator<KeyValuePair<string, string>> GetEnumerator()
    {
        for (var i = 0; i < _values.Length; i++) yield return KeyValuePair.Create(_layout.Keys[i], _values[i]);
    }

    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

    public bool Equals(VariantMap? other) =>
        other is not null && (ReferenceEquals(this, other)
            || (_layout.Keys.SequenceEqual(other._layout.Keys, StringComparer.Ordinal)
                && _values.SequenceEqual(other._values, StringComparer.Ordinal)));

    public override bool Equals(object? obj) => Equals(obj as VariantMap);

    public override int GetHashCode()
    {
        var hash = new HashCode();
        foreach (var v in _values) hash.Add(v, StringComparer.Ordinal);
        return hash.ToHashCode();
    }

    public override string ToString() => "{ " + string.Join(", ", this.Select(kv => $"{kv.Key} = {kv.Value}")) + " }";
}
