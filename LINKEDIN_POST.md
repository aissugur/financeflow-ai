# LinkedIn Post

> Replace `[demo link]` and `[repo link]` before posting. Keep it short.

---

I built a small project to learn how to make AI answers you can actually trust:
**FinanceFlow AI** — a source-backed assistant for business documents.

You upload an invoice, contract, or payment note and ask a question in plain
English. Instead of guessing, it:

• answers **only** from the retrieved passages
• shows the **citation** — the exact source excerpt behind every answer
• **abstains** ("Not enough information in the uploaded document") when the
  evidence isn't there

The part I learned the most from wasn't the model — it was the **evaluation**. I
wrote a small golden dataset and measured citation coverage, correct abstentions,
and "unsupported answers" (answers with no evidence). The goal was 0 unsupported
answers, and treating a correct refusal as a success rather than a failure.

Stack: FastAPI + React + SQLite, a custom TF-IDF retriever, optional LLM layer.
It runs fully offline with no API key, has tests + CI, and a one-click demo.

Still plenty to improve (embeddings for paraphrased questions is next), but it was
a good way to practice building trustworthy, grounded AI for a real workflow.

Demo: [demo link] · Code: [repo link]

#AI #RAG #FastAPI #React #FinTech #MachineLearning
