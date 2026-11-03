package com.example.clean.architecture.infrastructure.controller;

import com.example.clean.architecture.domain.core.Either;
import com.example.clean.architecture.domain.core.Validation;
import com.example.clean.architecture.domain.services.ExampleService;
import com.example.clean.architecture.usecase.audiolib.params.ExampleUseCaseParams;
import com.example.clean.architecture.usecase.core.UseCase;
import com.example.clean.architecture.usecase.response.VoidResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Controller;

@Controller
public class ExampleController implements ExampleService {
  
  private static final Logger log = LoggerFactory.getLogger(ExampleController.class);
  
  private final UseCase<ExampleUseCaseParams, VoidResponse> useCaseNotification;
  
  public ExampleController(final UseCase<ExampleUseCaseParams, VoidResponse> exampleUseCase) {
    this.useCaseNotification = exampleUseCase;
  }
  
  @Override
  public String execute(final String message) {
    final Either<Validation, VoidResponse> responses = this.useCaseNotification.execute(
        this.toParams(message));
    if (responses.isRight()) {
      return message;
    } else {
      responses.getLeft().getErrors().forEach(log::error);
      return "ERROR";
    }
  }
  
  @Override
  public String getVersion() {
    return "1.0.0";
  }
  
  private ExampleUseCaseParams toParams(final String message) {
    return new ExampleUseCaseParams(message);
  }
}
