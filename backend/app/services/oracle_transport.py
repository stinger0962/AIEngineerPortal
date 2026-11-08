"""Per-reading SDK options without changing shared portal AI defaults."""


def interactive_oracle_client(client):
    # Anthropic's default retries can repeat a costly/ambiguous generation before
    # the caller knows whether it ran. A person can retry using our request key.
    configure = getattr(client, "with_options", None)
    if not callable(configure):
        raise TypeError("Oracle client must support explicit timeout and retry options")
    return configure(max_retries=0, timeout=60.0)
