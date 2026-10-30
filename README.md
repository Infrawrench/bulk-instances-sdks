# Infrawrench bulk-instances SDKs

AWS instance attributes and prices, with their full history, from the bundles
Infrawrench publishes at `instances-bundles.infrawrench.com`: EC2, RDS, ElastiCache,
OpenSearch, Redshift, DocumentDB, Neptune, MemoryDB, DAX, SageMaker, EMR and GameLift.
Each SDK downloads a platform's bundle, caches it in `~/.infrawrench/aws_pricing_data`,
and decodes instances lazily. They share the cache format, so one downloaded bundle
serves all of them.

| Language   | Directory          | Install                                                    |
| ---------- | ------------------ | ---------------------------------------------------------- |
| TypeScript | [`ts/`](ts)        | `npm install @infrawrench/bulk-instances`                  |
| Python     | [`python/`](python) | `pip install infrawrench-bulk-instances`                  |
| Ruby       | [`ruby/`](ruby)    | `gem install infrawrench-bulk_instances`                   |
| Java       | [`java/`](java)    | `com.infrawrench:bulk-instances`                           |
| C#         | [`csharp/`](csharp) | `dotnet add package Infrawrench.BulkInstances`            |
| Rust       | [`rust/`](rust)    | `cargo add infrawrench-bulk-instances`                     |
| PHP        | [`php/`](php)      | `composer require infrawrench/bulk-instances`              |
| Go         | [`go/`](go)        | `go get github.com/infrawrench/bulk-instances-sdks/go`     |

Each SDK can also fetch a single instance from the Infrawrench API
(`/api/v1/aws-bulk-pricing/<platform>/<instance>`) without downloading the whole bundle.

Each directory's README covers that SDK's API. Any Infrawrench bearer credential works
as the token, and every SDK defaults to `INFRAWRENCH_API_KEY`.

## Conformance

[`conformance/`](conformance) holds a fixture bundle, a fake bundles server, and the
TypeScript SDK's decoded output. CI runs every SDK against it, so the ports stay
identical in what they decode and in how they download, cache and fail:

```sh
conformance/run.sh <typescript|python|ruby|java|csharp|rust|php|go>
```

## Releasing

Bump the version in every manifest, merge, then push a tag:

```sh
git tag v1.0.1 && git push origin v1.0.1
```

[`publish.yml`](.github/workflows/publish.yml) checks that every manifest carries the
tag's version, then publishes to npm, PyPI, RubyGems, Maven Central, NuGet and
crates.io, tags `go/v1.0.1` for Go, and mirrors `php/` to the Packagist repository.

## License

MIT. See [LICENSE](LICENSE).
