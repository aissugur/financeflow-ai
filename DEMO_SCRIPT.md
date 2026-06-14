# Demo Script — 60-second Loom

Setup before recording: backend running on `:8000`, frontend on `:5173`, browser
on the **Overview** page, screen clean. Speak calmly; let the UI do the work.

---

**0–10s — Problem**
> "Finance teams answer the same questions from invoices and contracts all day —
> what's the total, when's it due, what's the payment term. A normal chatbot will
> just make up a number. FinanceFlow only answers from the document, with
> citations — and refuses when it can't."

*(On screen: the Overview hero + the four trust badges.)*

**10–20s — Upload / demo document**
> "I'll load the sample documents in one click."

*(Click **Try Demo**. It seeds an invoice, a contract, and a payment note, and
jumps to the Ask workspace.)*

**20–35s — Ask a supported question**
> "It already answered 'What is the total amount due?' — and here's the answer."

*(The answer card shows the figure with a green "cited" badge. Point at it.)*

**35–45s — Show citations / evidence**
> "On the right is the exact source passage it used — document, chunk, and the
> highlighted line `Total Amount Due $2,413.98`. Every answer is verifiable."

*(Hover/expand an item in the Evidence panel.)*

**45–55s — Ask an unsupported question → abstention**
> "Now something the document doesn't contain — a social security number."

*(Click the "Correctly abstains" chip. The amber card shows: "Not enough
information in the uploaded document." with no citation.)*
> "It refuses instead of guessing. That's the whole point in finance."

**55–60s — Evaluation + closing line**
*(Click **Evaluation → Run**.)*
> "And I measure that: a golden-dataset eval — 100% citation coverage, zero
> unsupported answers. Source-backed AI you can actually trust."

---

**One-line close (if you have a spare second):**
> "Built with FastAPI, React, and a custom retriever — runs fully offline."
