"""第5回 発展: search_outline の構造テスト（APIを呼ばず、検索結果を差し替えて確かめる）。"""

from app import retrieval


def test_outline_lists_whole_section_of_each_hit_once(monkeypatch):
    pages = retrieval.load_pages()
    first, second = pages[10], pages[11]  # 同じ章の隣り合うページ
    fake = [{**first, "distance": 0.1}, {**second, "distance": 0.2}]
    monkeypatch.setattr(retrieval, "search", lambda query: fake)

    result = retrieval.search_outline("テスト")

    assert [seed["page_id"] for seed in result["seeds"]] == [first["page_id"], second["page_id"]]
    sections = [(item["document_title"], item["section"]) for item in result["outline"]]
    assert len(sections) == len(set(sections))  # 同じ章は1回だけ
    listed = {page["page_id"]: page["fetched"] for item in result["outline"] for page in item["pages"]}
    assert listed[first["page_id"]] and listed[second["page_id"]]  # 本文を返したページは fetched=True
    assert not all(listed.values())  # 章の他のページは fetched=False で、タイトルだけ載る
