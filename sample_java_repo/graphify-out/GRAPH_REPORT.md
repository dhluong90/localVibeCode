# GRAPH_REPORT.md — Deterministic AST Knowledge Graph

## 1. Architectural God Nodes (Core Centrality Ranking)
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java`** (Score: `16`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/validate/UseCaseParamsValidation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java']`
- **`clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java`** (Score: `15`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCaseParams.java', 'clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java`** (Score: `13`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCaseParams.java']`
- **`clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java`** (Score: `12`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java']` | Outbound Imports: `[]`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java`** (Score: `12`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java']` | Outbound Imports: `[]`
- **`clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java`** (Score: `10`) — Module | Inbound Callers: `['clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/ExampleControllerTest.java', 'clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/services/ExampleService.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java`** (Score: `10`) — Module | Inbound Callers: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/validate/UseCaseParamsValidation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/Invalid.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationSupport.java']` | Outbound Imports: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/Invalid.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationSupport.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java`** (Score: `9`) — Module | Inbound Callers: `['clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java', 'clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java`** (Score: `7`) — Module | Inbound Callers: `[]` | Outbound Imports: `['clean-architecture-boot/src/main/java/com/example/clean/architecture/Application.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/services/ExampleService.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java`** (Score: `7`) — Module | Inbound Callers: `['clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/ExampleControllerTest.java']` | Outbound Imports: `['clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/services/ExampleService.java`** (Score: `6`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/e2e/DummyTestITCase.java', 'clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java', 'clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java']` | Outbound Imports: `[]`
- **`clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java`** (Score: `6`) — Module | Inbound Callers: `['clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java']` | Outbound Imports: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCaseParams.java`** (Score: `5`) — Module | Inbound Callers: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java']` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationSupport.java`** (Score: `5`) — Module | Inbound Callers: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/validate/UseCaseParamsValidation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java']` | Outbound Imports: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java']`
- **`clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java`** (Score: `5`) — Module | Inbound Callers: `[]` | Outbound Imports: `['clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java']`
- **`clean-architecture-boot/src/main/java/com/example/clean/architecture/Application.java`** (Score: `4`) — Module | Inbound Callers: `['clean-architecture-boot/src/test/java/com/example/clean/architecture/e2e/DummyTestITCase.java', 'clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java']` | Outbound Imports: `[]`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/validate/UseCaseParamsValidation.java`** (Score: `4`) — Module | Inbound Callers: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java']` | Outbound Imports: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java', 'clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationSupport.java']`
- **`clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/Invalid.java`** (Score: `3`) — Module | Inbound Callers: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java']` | Outbound Imports: `['clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java']`
- **`clean-architecture-boot/src/test/java/com/example/clean/architecture/e2e/DummyTestITCase.java`** (Score: `2`) — Module | Inbound Callers: `[]` | Outbound Imports: `['clean-architecture-boot/src/main/java/com/example/clean/architecture/Application.java', 'clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/services/ExampleService.java']`
- **`clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/ExampleControllerTest.java`** (Score: `2`) — Module | Inbound Callers: `[]` | Outbound Imports: `['clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java', 'clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java']`
- **`clean-architecture-boot/src/main/java/com/example/clean/architecture/config/AppConfiguration.java`** (Score: `0`) — Module | Inbound Callers: `[]` | Outbound Imports: `[]`

## 2. Repository Structural Skeleton (Signatures Only)

### File: `clean-architecture-boot/src/main/java/com/example/clean/architecture/Application.java`
  - `public class Application`
    - `public static void main(String[] args)`

### File: `clean-architecture-boot/src/main/java/com/example/clean/architecture/config/AppConfiguration.java`
  - `public class AppConfiguration`

### File: `clean-architecture-boot/src/test/java/com/example/clean/architecture/e2e/DummyTestITCase.java`
  - `class DummyTestITCase`

### File: `clean-architecture-boot/src/test/java/com/example/clean/architecture/it/DummyTestIT.java`
  - `class DummyTestIT`

### File: `clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Either.java`
  - `public abstract class Either<L, R> implements Iterable<R>, Serializable`
    - `public static <L, R> Either<L, R> right(final R right)`
    - `public static <L, R> Either<L, R> left(final L left)`
    - `public static <L, R> Either<L, R> narrow(final Either<? extends L, ? extends R> either)`
    - `public L getLeft()`
    - `public boolean isLeft()`
    - `public boolean isRight()`
    - `public final <U> U transform(final Function<? super Either<L, R>, ? extends U> f)`
    - `public final R getOrElseGet(final Function<? super L, ? extends R> other)`
    - `public final R getOrElse(final R other)`
    - `public final void orElseRun(final Consumer<? super L> action)`
    - `public final Either<R, L> swap()`
    - `public final Either<L, R> recover(final Function<? super L, ? extends R> recoveryFunction)`
    - `public final <U> Either<L, U> map(final Function<? super R, ? extends U> mapper)`
    - `public final <U> Either<U, R> mapLeft(final Function<? super L, ? extends U> leftMapper)`
    - `public final Optional<Either<L, R>> filter(final Predicate<? super R> predicate)`
    - `public final Optional<Either<L, R>> filterNot(final Predicate<? super R> predicate)`
    - `public R get()`
    - `public final boolean isEmpty()`
    - `public final Either<L, R> orElse(final Either<? extends L, ? extends R> other)`
    - `public final Iterator<R> iterator()`
    - `public final Either<L, R> peek(final Consumer<? super R> action)`
    - `public final Either<L, R> peekLeft(final Consumer<? super L> action)`
    - `public boolean equals(final Object obj)`
    - `public int hashCode()`
    - `public String stringPrefix()`
    - `public String toString()`

### File: `clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/core/Validation.java`
  - `public final class Validation`
    - `public static Validation empty()`
    - `public static Validation of(final String error)`
    - `public List<String> getErrors()`
    - `public void addError(final String error)`
    - `public void addErrors(final List<String> error)`
    - `public boolean hasErrors()`
    - `public <T extends RuntimeException> T as(final Function<List<String>, T> supplier)`
    - `public Validation or(final Supplier<Validation> s)`
    - `public <T> Either<Validation, T> asEither()`

### File: `clean-architecture-domain/src/main/java/com/example/clean/architecture/domain/services/ExampleService.java`
  - `public interface ExampleService`

### File: `clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/bean/management/BeanInitializer.java`
  - `public class BeanInitializer`
    - `public UseCase<ExampleUseCaseParams, VoidResponse> sendEventMessage()`

### File: `clean-architecture-infrastructure/src/main/java/com/example/clean/architecture/infrastructure/controller/ExampleController.java`
  - `public class ExampleController implements ExampleService`
    - `public String execute(final String message)`
    - `public String getVersion()`
    - `private ExampleUseCaseParams toParams(final String message)`

### File: `clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/ExampleControllerTest.java`
  - `public class ExampleControllerTest`
    - `public void testGetVersion()`

### File: `clean-architecture-infrastructure/src/test/java/com/example/clean/architecture/infrastructure/controller/config/ExampleControllerConfig.java`
  - `public class ExampleControllerConfig extends BeanInitializer`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/ExampleUseCase.java`
  - `public class ExampleUseCase implements UseCase<ExampleUseCaseParams, VoidResponse>`
    - `public Either<Validation, VoidResponse> execute(final ExampleUseCaseParams params)`
    - `private VoidResponse doAction()`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/ExampleUseCaseParams.java`
  - `public class ExampleUseCaseParams implements UseCaseParams`
    - `public Validation validate()`
    - `public boolean equals(Object o)`
    - `public int hashCode()`
    - `public String toString()`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/audiolib/params/validate/UseCaseParamsValidation.java`
  - `public interface UseCaseParamsValidation extends Function<String, ValidationResult>`
    - `private static UseCaseParamsValidation holds(final Predicate<String> p, final String message)`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCase.java`
  - `public interface UseCase<T extends UseCaseParams, R>`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/UseCaseParams.java`
  - `public interface UseCaseParams`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/Invalid.java`
  - `public class Invalid implements ValidationResult`
    - `public boolean isValid()`
    - `public Optional<List<String>> getReasons()`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationResult.java`
  - `public interface ValidationResult`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/core/validation/ValidationSupport.java`
  - `public class ValidationSupport`
    - `public boolean isValid()`
    - `public Optional<List<String>> getReasons()`
    - `public static ValidationResult zip(final ValidationResult left, final ValidationResult right)`
    - `public static <T> Stream<T> toStream(final Optional<T> optional)`

### File: `clean-architecture-usecases/src/main/java/com/example/clean/architecture/usecase/response/VoidResponse.java`
  - `public class VoidResponse`
    - `public static VoidResponse ok()`
    - `public static VoidResponse empty()`

### File: `clean-architecture-usecases/src/test/java/com/example/clean/architecture/ExampleUseCaseTest.java`
  - `class ExampleUseCaseTest`
