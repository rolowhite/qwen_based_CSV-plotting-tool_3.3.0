"""Ceasar: a local data-analysis assistant. Everything here works without a window.

  sandbox   runs the pandas code (a task's or the model's) on a copy of the table, after checking it
  profile   what a table looks like: types, gaps, duplicates, messy columns (also the model's briefing)
  diff      what a piece of code changed in the table
  tasks     the starter tasks: reports and clean-ups, each one just pandas code that is shown and can be undone
  agent     the chat with the local Ollama model: an instruction in, code (checked, run, retried) out
"""
