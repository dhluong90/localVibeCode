# AGENTS.md — instructions for the AI coding agent (OpenCode)

> Copy to the repository root as `AGENTS.md` and fill in the brackets. Keep it short: the local
> model has a limited context window, every line here is read on every task.

## Project
- [One sentence: what this service/application does.]
- Modules: [module → responsibility, one line each].

## Build & test (offline)
- Build one module and what it depends on: `mvn -o -q -pl <module> -am -DskipTests install`
- Test one module: `mvn -o -q test -pl <module> -am -Dtest='<package>.**' -Dsurefire.failIfNoSpecifiedTests=false`
- Always run the tests of every module you changed before saying you are done.

## Rules
- Make the smallest change that satisfies the task; do not refactor unrelated code.
- Never modify or delete existing tests to make them pass. Add new tests next to the existing ones.
- Follow the existing style: [Google Java Style, 2 spaces / 4 spaces], [formatter command].
- Do not add dependencies without being asked.
- Security: validate identifiers from the request path against the payload; never trust client-supplied ids.

## Where things are
- [Controllers: …] [Services: …] [Repositories / entities: …] [Tests: <module>/src/test/java/…]
