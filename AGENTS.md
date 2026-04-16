# Agent instructions

## Prompts
- if the user provides a `.txt` file under `prompts/`, treat the entire file contents as the user prompt/instructions for this task. Do not treat it as documentation to summarize or update.

## Output to terminal
- when you print to the terminal print in unicode
- use symbols/subscripts for math equations so they are **human readable** on the terminal, don't use undersocres (_) and carrots(^)
- when printing URLs to the terminal, format them in single quotes like `'https://example.com'` so they stay clickable in PowerShell

## Intermediary outputs
- if you generate a re-usable script for a task save it to scripts/
- if you generate images, text, etc. as an intermediary step for some pipeline, you can save those files to assets/ in case you may need to go back to review them later

## Environment
- prioritize using the `codex` conda environment for python commands, scripts, and tooling
- Examples:
  - conda run -n codex python .\script.py
  - conda run -n codex python -c "print('hello from codex')"
  - You can use the absolute path if something breaks with the conda wrapper: {path\to\conda\env}\codex\python.exe 
- if you need to install packages, install them into the `codex` conda environment


## Analyzing documents
- If you need to save any intermediary output for analyzing/converting documents (rendering images etc.) save those in the assets\ folder
- In general, if you convert/read documents save them in a format you can re-read (txt,img etc) instead of in their raw doc, ppt, and pdf formats. 

### PDFs documents
- use the pdf skill to analyze pdfs
  - Prioritize using python for document processing instead of latex
  - if you need a python package installed for the pdf skill install it

### Word documents
- Use the doc skill to analyze 

### Ppt documents
- Use the slides skill to analyze 
