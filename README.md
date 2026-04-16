# Accessible Slides Agent Setup

This directory is a lightweight workspace for collaborating with an AI agent to review and improve the accessibility of slide decks.

It is intended for instructors who build slides from LaTeX, Markdown, or similar text-based sources and then compile those sources to PDF for review.

## Required Programs

You will need:

- A text-to-PDF slide workflow of your choice, such as MiKTeX, Obsidian, Marp, or another compiler/export tool you already use.
- `veraPDF`, the open-source PDF validator available from `'https://verapdf.org'`.

## How To Use This Setup

1. Check out agent instructions in AGENTS.md, feel free to keep or modify those. This is just what works for me (this can sometimes get overriden by a prompt, or the agent can sometimes just "forget" these instructions as well).
Put reusable agent prompts in `prompts/`.
2. Spin up a CLI agent of your choice
  - `codex` is free for all Cal Poly staff/students (for now)
  - claude code, gemini, etc. should all work too
3. Create a reusable prompt like `prompts/accessibility.txt`
  - This took me a few tries to refine. had to work with the agent to refine the right workflow, update its process, and then ask it to modify its own prompt based on results
4. Compile your slides to PDF with your normal workflow.
5. Pass the prompt, raw file, and generated slides to the agent, something like: 
`$ prompts/accessibility.txt slides.pdf slides.md`
  - The main idea here is to allow the agent to run a loop testing them to see if they get a full pass from verapdf, continue making updates until it passes. it stores the final results in a subfolder called `accessible` and doesn't modify your original slides.
6. Go back and review the new accessible slides
  - double check that img alt text makes sense
  - most agents can "view" pdfs by basically taking a screenshot. sometimes this works, but sometimes they clobber your existing formatting so be careful here too. 


## Folder Guide

### `AGENTS.md`

This file gives the agent local instructions for working in this directory. It tells the agent how to handle prompts, where to save intermediary files, which Python environment to prefer, and which workflow to use when analyzing PDFs, Word documents, and PowerPoint files.

### `prompts/`

This directory stores reusable prompt files for the agent.

### `prompts/accessibility.txt`

An example prompt for accessible slide review. You can reuse it directly or adapt it for a specific course, deck, or workflow.

### `scripts/`

Use this folder for reusable scripts the agent creates while analyzing, converting, or checking slide materials.

### `assets/`

Use this folder for intermediary outputs such as extracted text, rendered page images, temporary analysis files, or other artifacts worth keeping during review.

## Required Dependencies

- CLI based agent (codex, claude code, etc.)
- CLI based PDF verifier (ex: verapdf)
- CLI based slide compilation

## Agent permissions

Generally this can be accomplished in a "sandboxed" mode for the agent, i.e. it can run programs that only modify files in your current directory. Some programs may call other programs that run outside "sandbox" permissions so your agent may ask you to verify that program.

## Results

VeraPDF generates an accessibility score out of 100. In general this setup has gotten my slides from the mid 90s to 100 consistently. 
100/100 on VeraPDF seems to also pass Canvas's checker. 
All slides are getting 100% on Canvas as well if they meet the full pass requirements from VeraPDF. 
