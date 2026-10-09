# Security

## Reporting a vulnerability

Please don't open a public issue for security problems. Use GitHub's private reporting: **Security → Report a vulnerability** on this repository. Include what you found, how to reproduce it and the affected server or script. You should get a reply within a week.

## Scope

Framewright runs locally. The MCP servers read and write the files the client asks for and run ffmpeg and local models; they have no network listener and no authentication of their own. Worth reporting:

- a tool parameter that leads to command injection or writes outside the intended path
- a crafted media or plan file that runs code
- model or binary downloads that skip checksum verification (`scripts/fetch_models.py` pins SHA-256)

## Read LLM-generated scripts before running them

The DaVinci Resolve scripts in this workflow are written by an LLM, and Resolve runs them with your user's permissions. **Read every generated script before you run it:**

- It should only call the Resolve API (`resolve`, project, media pool, timeline). `prompts/resolve-script.md` forbids `io`, `require` and file writes; reject a script that uses them.
- It should only touch the files named in your edit plan.
- It should never delete timelines or media.
- Prefer the bundled `resolve/scripts/Edit/Framewright/framewright_build_plan.lua`, which builds any valid plan without generated code.

Treat edit plans and prompts from other people the same way: a plan is data, but a script is code.
