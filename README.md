# Telangana Grade 8 AI Tutor — RAG first, fine-tuning next

This is the first runnable local RAG implementation using the initial corpus
prepared from the uploaded Telangana Class VIII PDFs.

## What it does
1. Embeds the initial textbook text chunks with Sentence Transformers.
2. Stores vectors and source metadata in a local Chroma database.
3. Retrieves the most relevant passages for a student's question.
4. Sends those passages to Qwen2.5 1.5B through Ollama.
5. Displays source PDF names and page numbers with the answer.

## Important source limitation
The current index includes Mathematics, Physical Sciences, Biology, English,
and Social Studies. Hindi and Telugu are excluded until their legacy-font text
is corrected with OCR/Unicode recovery. The current chunks are page-grounded,
but not yet fully chapter-labelled or manually verified. Answers should be
tested against the original PDFs before classroom use.

## Windows setup

Open PowerShell in this project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Ollama for Windows from its official website, then open a new terminal
and run:

```powershell
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b
```

Wait for the model to load. You can type `/bye` to leave the Ollama prompt.
Keep Ollama running in the background.

Build the local vector index:

```powershell
python build_index.py
```

Start the tutor:

```powershell
streamlit run app.py
```

Streamlit will show a local URL, usually `http://localhost:8501`.

## If the laptop is slow
The first embedding-model download and first index build may take time. Close
unneeded applications. This project uses CPU embeddings and Ollama CPU inference
on your Intel integrated-graphics laptop. Start with short questions.

## Fine-tuning comes after RAG validation
Do not fine-tune on raw PDF chunks as if they were question-answer examples.
Next we will:
- repair Hindi/Telugu extraction;
- inspect retrieval quality and source correctness;
- create verified instruction/answer examples with citations;
- split training and validation examples;
- fine-tune a suitable base model with LoRA/QLoRA on a cloud GPU;
- evaluate it against a held-out textbook question set;
- package the adapter/merged model for Ollama if the model format is supported.

RAG and fine-tuning serve different purposes: RAG supplies the current textbook
evidence; fine-tuning adapts the model's response behaviour and teaching style.
