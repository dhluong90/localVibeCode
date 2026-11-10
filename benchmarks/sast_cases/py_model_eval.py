class Model:
    def eval(self) -> None:
        self.training = False


def predict(model: Model) -> None:
    model.eval()
