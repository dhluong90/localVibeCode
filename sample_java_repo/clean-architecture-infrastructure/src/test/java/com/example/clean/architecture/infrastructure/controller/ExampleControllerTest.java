package com.example.clean.architecture.infrastructure.controller;

import com.example.clean.architecture.infrastructure.controller.config.ExampleControllerConfig;
import static org.assertj.core.api.Assertions.assertThat;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

class ExampleControllerTest {
  private ApplicationContextRunner runner;

  @BeforeEach
  void setUp() {
    this.runner = new ApplicationContextRunner()
        .withUserConfiguration(ExampleControllerConfig.class);
  }

  @Test
  void testContextOk() {
    this.runner
        .run(context -> {
          assertThat(context).hasSingleBean(ExampleControllerConfig.class);
        });
  }

  @Test
  void executeControllerWithoutErrors() {
    this.runner
        .run(context -> {
          final ExampleController notificationController = context.getBean(ExampleController.class);
          final String result = notificationController.execute("Message action");
          assertThat(result).isEqualTo("Message action");
        });
  }

  @Test
  void executeControllerWithErrors() {
    this.runner
        .run(context -> {
          final ExampleController notificationController = context.getBean(ExampleController.class);
          final String result = notificationController.execute("").trim();
          assertThat(result).isEqualTo("ERROR");
        });
  }

  @Test
  void testGetVersion() {
    this.runner
        .run(context -> {
          final ExampleController controller = context.getBean(ExampleController.class);
          assertThat(controller.getVersion()).isEqualTo("1.0.0");
        });
  }

  @Test
  void testSystemStatus() {
    this.runner
        .run(context -> {
          final ExampleController controller = context.getBean(ExampleController.class);
          assertThat(controller.getSystemStatus()).isEqualTo("SYSTEM_OPERATIONAL");
        });
  }
}
