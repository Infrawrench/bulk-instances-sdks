use std::fmt;

type Source = Box<dyn std::error::Error + Send + Sync + 'static>;

/// Returned when the pricing data cannot be downloaded. [`status`](Error::status) is the HTTP
/// status, if there was a response.
///
/// Failures without a response (connection refused, DNS, a cache that cannot be written) keep
/// their cause as the [`source`](std::error::Error::source).
#[derive(Debug)]
pub struct Error {
    message: String,
    status: Option<u16>,
    source: Option<Source>,
}

impl Error {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
            status: None,
            source: None,
        }
    }

    pub(crate) fn with_status(message: impl Into<String>, status: u16) -> Self {
        Self {
            message: message.into(),
            status: Some(status),
            source: None,
        }
    }

    pub(crate) fn with_source(message: impl Into<String>, source: impl Into<Source>) -> Self {
        Self {
            message: message.into(),
            status: None,
            source: Some(source.into()),
        }
    }

    /// The HTTP status, if there was a response.
    pub fn status(&self) -> Option<u16> {
        self.status
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        self.source.as_deref().map(|e| e as _)
    }
}
