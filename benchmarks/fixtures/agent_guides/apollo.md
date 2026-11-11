
## Navigating this repository (for the AI agent)
- This is a multi-module Maven repo. Source files are under `<module>/src/main/java/com/ctrip/framework/apollo/...`
  and tests under `<module>/src/test/java/...`. Paths never start with `src/` at the repository root.
- Modules: `apollo-common` (shared DTOs/utils), `apollo-biz` (entities, repositories, business services),
  `apollo-configservice` (config/notification APIs, caches), `apollo-adminservice` (admin REST APIs),
  `apollo-portal` (portal web app, permissions, OpenAPI), `apollo-audit/*` (audit log).
- To find a class, use glob with `**/ClassName.java` (e.g. `**/ReleaseService.java`). To find a method, grep for
  its name and read only the surrounding lines.
- Files here are large. Do NOT read whole files: grep for the method first, then read with an offset and a limit of
  about 80 lines around it. Keep the context small.
- Make the change with the edit tool as soon as you have located the code. Then run the module's tests.
