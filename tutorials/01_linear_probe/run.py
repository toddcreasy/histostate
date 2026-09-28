"""Step 1: linear probe on NCT-CRC-HE with frozen Phikon-v2 features.

Train on the 1k subset, test on the separate 7k validation cohort
(different patients, different lab). Nine colorectal tissue classes.

Run from the repo root:
    uv run python tutorials/01_linear_probe/run.py
"""

from pathlib import Path

import mlflow
from datasets import load_dataset
from sklearn.metrics import balanced_accuracy_score, classification_report

from histostate.device import get_device
from histostate.features import DEFAULT_BACKBONE, TileEncoder, load_or_extract
from histostate.probe import LinearProbe, ProbeConfig, predict, train_probe

DATASET = "owkin/nct-crc-he"
TRAIN_SPLIT = "nct_crc_he_1k"
TEST_SPLIT = "crc_val_he_7k"
CACHE = Path("data/features")


def main() -> None:
    device = get_device()
    print(f"Device: {device}")

    train_ds = load_dataset(DATASET, split=TRAIN_SPLIT)
    test_ds = load_dataset(DATASET, split=TEST_SPLIT)
    class_names = train_ds.features["label"].names

    # One encoder, created lazily so cached runs skip loading the model.
    encoder = None

    def get_encoder() -> TileEncoder:
        nonlocal encoder
        if encoder is None:
            encoder = TileEncoder(DEFAULT_BACKBONE, device)
        return encoder

    print("Embedding train split")
    x_train, y_train = load_or_extract(
        CACHE / f"{TRAIN_SPLIT}.pt", get_encoder, train_ds
    )
    print("Embedding test split")
    x_test, y_test = load_or_extract(CACHE / f"{TEST_SPLIT}.pt", get_encoder, test_ds)
    print(f"Train {tuple(x_train.shape)}, test {tuple(x_test.shape)}")

    config = ProbeConfig()
    mlflow.set_experiment("histostate-01-linear-probe")
    with mlflow.start_run():
        mlflow.log_params({"backbone": DEFAULT_BACKBONE, **config.model_dump()})

        def log_epoch(epoch: int, loss: float) -> None:
            mlflow.log_metric("train_loss", loss, step=epoch)
            if epoch % 5 == 0 or epoch == config.epochs - 1:
                print(f"  epoch {epoch:3d}  loss {loss:.4f}")

        model = LinearProbe(x_train.shape[1], len(class_names))
        model = train_probe(model, x_train, y_train, config, device, log_epoch)

        y_pred = predict(model, x_test, device)
        bal_acc = balanced_accuracy_score(y_test, y_pred)
        mlflow.log_metric("test_balanced_accuracy", bal_acc)

    print(f"\nTest balanced accuracy: {bal_acc:.3f}\n")
    print(classification_report(y_test, y_pred, target_names=class_names, digits=3))


if __name__ == "__main__":
    main()
