# Problem

People without specialized software like NotePad++ / AI don't have an easy way of converting line endings of an application. If only there was another specialized application that can do it for them....

## Initial requirements

<!-- Give every requirement an ID so tests can cite it later:-->

R1. Terminal command app, targeting a file or directory, tell the user which files have valid line endings that can be changed, and if so, what to change the line ending to
R2. Small cache of recently changed files (singular and batched) so the user is aware of what they've changed and if they need to revert it
