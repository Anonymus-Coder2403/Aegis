import pytest

from aegis.billing.rag import embeddings


class _FakeVector:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


@pytest.fixture(autouse=True)
def reset_model_cache():
    embeddings._MODEL = None
    yield
    embeddings._MODEL = None


def test_embed_text_uses_sentence_transformer_and_returns_float_list(monkeypatch):
    calls = []

    class FakeModel:
        def encode(self, text):
            calls.append(("encode", text))
            return _FakeVector([1, 2, 3])

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            calls.append(("init", model_name))
            self.model = FakeModel()

        def encode(self, text):
            return self.model.encode(text)

    monkeypatch.setattr(embeddings, "SentenceTransformer", FakeSentenceTransformer)

    result = embeddings.embed_text("bill text")

    assert result == [1.0, 2.0, 3.0]
    assert calls == [
        ("init", embeddings.EMBEDDING_MODEL_NAME),
        ("encode", "bill text"),
    ]


def test_embed_text_loads_model_lazily(monkeypatch):
    init_calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            init_calls.append(model_name)

        def encode(self, text):
            return [0, 1, 2]

    monkeypatch.setattr(embeddings, "SentenceTransformer", FakeSentenceTransformer)

    assert init_calls == []

    embeddings.embed_text("first call")

    assert init_calls == [embeddings.EMBEDDING_MODEL_NAME]


def test_embed_text_reuses_cached_model_instance(monkeypatch):
    init_calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            init_calls.append(model_name)

        def encode(self, text):
            return [len(text), 1, 2]

    monkeypatch.setattr(embeddings, "SentenceTransformer", FakeSentenceTransformer)

    first = embeddings.embed_text("one")
    second = embeddings.embed_text("two")

    assert first == [3.0, 1.0, 2.0]
    assert second == [3.0, 1.0, 2.0]
    assert init_calls == [embeddings.EMBEDDING_MODEL_NAME]


def test_embed_text_raises_runtime_error_on_model_load_failure(monkeypatch):
    class FailingSentenceTransformer:
        def __init__(self, model_name):
            raise ValueError("broken model")

    monkeypatch.setattr(embeddings, "SentenceTransformer", FailingSentenceTransformer)

    with pytest.raises(RuntimeError) as exc_info:
        embeddings.embed_text("bill text")

    assert embeddings.EMBEDDING_MODEL_NAME in str(exc_info.value)
    assert "broken model" in str(exc_info.value)
