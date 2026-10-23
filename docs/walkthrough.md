# Walkthrough

How this project went from fitting a line to a 94.7% tissue classifier, one stage at a time, with
the numbers each step produced and what went wrong along the way. Read it next to the code: every
stage is one script in `scripts/`, and each section says what to run.

All numbers below come from real runs in this repo. Validation numbers use MedMNIST's validation
split; "shift-val" and "final test" are explained in [step 6](#6-build-a-validation-set-that-can-see-the-shift).

## Terms used throughout

- **Weights**: the numbers a model learns. Training nudges them to lower the loss.
- **Loss**: one number for how wrong the model is. Here it's cross-entropy: it punishes confident
  wrong answers hardest. A model guessing evenly across 9 classes scores ln 9 = 2.197.
- **Gradient**: for each weight, which direction and how much it should move to lower the loss.
  PyTorch computes it for you (autograd).
- **Epoch**: one pass over all the training images.
- **Learning rate (lr)**: how big a step each update takes.
- **Recall**: of the tiles that really are stroma, the share the model called stroma.

## 0. Warm-up: fit a line by gradient descent

`uv run python scripts/warmup_fit_line.py [--lr 0.01] [--steps 1000]`

Two weights, `w` and `b`, fit to noisy points from `y = 2x + 1`. No neural network, no dataset.
The point is to watch gradient descent work where you can check the answer by eye.
`tests/test_warmup_gradients.py` derives the mean-squared-error gradients by hand and checks
autograd against them, then checks `torch.optim.SGD` against a hand-written update.

Try a few `--lr` values. Too small crawls; too large overshoots.

## 1. Logistic regression on pixels

`uv run python scripts/stage1_logreg.py`

Flatten each 28x28 color tile into 2,352 numbers and learn one weight per pixel per class
(2,352 x 9, plus 9 biases). Softmax and cross-entropy are written by hand in
`src/histostate/softmax.py`, including the max-subtraction trick that keeps huge scores from
overflowing.

**Result: about 47% validation accuracy**, against 14.3% for always guessing the biggest class.
Train loss 1.30, validation loss 1.39: the model underfits, meaning it's too simple to fit even
the training data. Adipose is easy (93.5% recall). Stroma, smooth muscle, and debris blur together.

## 2. A multilayer perceptron

`uv run python scripts/stage2_mlp.py [--hidden 256]`

Add one hidden layer with a ReLU (rectified linear unit, `max(0, x)`) between two linear layers.
First written with raw weight tensors, then rebuilt with `nn.Linear` in `src/histostate/mlp.py`;
`tests/test_mlp.py` proves both versions compute the same thing.

| Hidden units | Weights | Train acc | Val acc | Gap |
|---|---|---|---|---|
| 64 | 151,177 | 69.3% | 63.7% | 5.6 |
| 256 | 604,681 | 72.6% | 65.2% | 7.4 |
| 1024 | 2,418,697 | 75.9% | 66.4% | 9.5 |

Up from 47%, but 16x more weights buys under 3 points, and the train/validation gap widens as
the model grows. That gap is **overfitting**: memorizing training tiles instead of learning
patterns that carry over. An MLP treats every pixel position separately, so it has to relearn
"nucleus" at every spot in the tile.

## 3. A small CNN

`uv run python scripts/stage3_cnn.py --size 28 --blocks 2 --no-augment --jitter 0 --epochs 15`

A CNN (convolutional neural network) slides small 3x3 filters across the image, so one learned
pattern works anywhere in the tile. `src/histostate/cnn.py`: two conv + ReLU + max-pool blocks,
then one linear layer. 47,625 weights, 13x fewer than the 256-unit MLP.
`tests/test_cnn.py` checks one convolution output by hand.

Plain SGD (stochastic gradient descent) kept collapsing: validation accuracy fell from 84% to 55%
mid-run at lr 0.03. Logging the gradient size every step showed spikes of 14 to 24 against a
typical 2.5. Two fixes, both in `scripts/stage3_cnn.py`:

- **Gradient clipping**: shrink any gradient longer than 5 back to length 5. Removed the collapses.
- **Cosine learning-rate decay**: start at 0.1 and glide toward 0 by the last epoch. Removed the
  remaining wobble.

The script also keeps the weights from the best validation epoch, not the last one.

**Result: 94.3% validation accuracy.** Normal mucosa recall went from 30% (MLP) to 91%.

## 4. The test set disagrees

`uv run python scripts/evaluate_test.py`

**94.3% on validation, 85.5% on test.** Stroma recall on test: 49%.

PathMNIST's validation set is a random slice of the same pool as training. Its test set comes
from a different clinical center, with different staining. Validation was measuring "how well
does this work on more of the same", which isn't the question.

## 5. Augmentation and longer training

Augmentation shows the model altered copies of training tiles so it can't memorize exact pixels.
`src/histostate/augment.py: flip_rotate` gives each tile one of its 8 mirror/rotation versions.
Tissue has no "up", so every version is still a valid example.

Three seeds each (a seed fixes the random starting weights and batch order; different seeds show
run-to-run noise):

| Setting | Val acc avg | Stroma recall avg |
|---|---|---|
| No augmentation, 15 epochs | 94.3% | 88.6% |
| Augmentation, 15 epochs | 95.2% | 88.9% |
| Augmentation, 30 epochs | 96.5% | 92.7% |
| Augmentation, 60 epochs | 97.5% | 94.1% |

Validation climbed to 97.6%. **Test only went from 85.5% to 87.2%**, and test loss was 1.36
against 0.079 on validation: the model was confidently wrong on the new center's tiles.
Tuning against validation can't fix a problem validation can't see.

## 6. Build a validation set that can see the shift

`src/histostate/splits.py: split_test` cuts the test set into two stratified halves (each class
split evenly):

- **Shift-val**: tune on this. It has the staining shift.
- **Final test**: score once, after all choices are made. Checking it repeatedly and picking
  whatever scores best turns it into another validation set.

Caveat: PathMNIST has no patient IDs, so the two halves can share patients.

Then target the shift directly. `color_jitter` (`--jitter`) randomly scales and shifts each
color channel of each training tile, mimicking slides stained darker, paler, or with one stain
stronger, so stain color stops being a reliable clue.
Shift-val accuracy, 3 seeds:

| Jitter | Val avg | Shift-val avg (range) |
|---|---|---|
| 0 | 97.6% (seed 0) | 86.1% (85.3 to 87.3) |
| 0.3 | 95.1% | 91.5% (90.9 to 92.2) |
| 0.5 | 94.0% | 91.0% (90.6 to 91.5) |

Validation went *down* and shift-val went *up* by 5 points. Note how much more the seeds
disagree under shift: a 2-point spread on shift-val against 0.3 on validation. One seed is not
enough to call a winner here.

**Final test, scored once: 91.4%, loss 0.26** (down from 1.36). Stroma recall 63%, muscle 76%:
those two get swapped for each other most.

## 7. Look inside the model

`uv run python scripts/inspect_cnn.py --model <a 28-pixel checkpoint>`

Saves the first-layer filters, the activation maps (where each filter fires) for a few tiles, and
the 20 tiles that most excite the channel that best separates stroma from muscle.

In the 28-pixel model that channel fired on dark, heavily stained tiles: its 20 strongest tiles
were a brick-red batch of muscle plus debris, and across stroma tiles its response correlated
about -0.8 with brightness. The model's best stroma/muscle feature was mostly a stain detector.
That's a **shortcut**: something correlated with the label in this data that breaks when staining
changes.

## 8. Resolution or depth?

MedMNIST also publishes PathMNIST at 64x64. More pixels means a bigger network, so this changed
two things at once: `--size 64` adds a third conv block (`--blocks 3`, 93,193 weights). A control
run, 28 pixels with 3 blocks, separates them. Shift-val, jitter 0.3, 3 seeds each:

| Model | Weights | Val | Shift-val (range) | Muscle recall | Stroma recall |
|---|---|---|---|---|---|
| 28 px, 2 blocks | 47,625 | 95.1% | 91.3% (90.3 to 92.2) | 74.5% | 68.2% |
| 28 px, 3 blocks | 61,513 | 96.1% | 91.8% (91.3 to 92.2) | 73.9% | 67.8% |
| 64 px, 3 blocks | 93,193 | 97.8% | 94.2% (93.9 to 94.6) | 82.2% | 78.2% |

(The 28 px, 2 block row reruns step 6's seed 0 on a different machine, so it differs slightly.)

The extra block adds a point on validation and nothing under shift. Resolution does the work.
Inspecting the 64-pixel model shows why: its best stroma/muscle channel now fires on long,
parallel, cigar-shaped nuclei, which is what smooth muscle looks like. All 20 of its strongest
tiles are muscle in ordinary pink stain, and its link to brightness roughly halved. At 28 pixels
that fiber shape is mostly gone, and a deeper model can't learn detail that isn't in the image.

**Final test for the 64-pixel model: 94.7%, loss 0.14.** Muscle recall 83%, stroma 75%.

## 9. Does 128 pixels help more?

`uv run python scripts/stage3_cnn.py --size 128` (a fourth conv block, `--blocks 4`, so the last
grid is still 8x8)

If 28 to 64 pixels bought 3 points, maybe 64 to 128 buys more. Same recipe, 3 seeds:

| Model | Weights | Val | Shift-val (range) | Muscle recall | Stroma recall | Time per epoch (T4) |
|---|---|---|---|---|---|---|
| 64 px, 3 blocks | 93,193 | 97.8% | 94.2% (93.9 to 94.6) | 82.2% | 78.2% | about 10 s |
| 128 px, 4 blocks | 130,121 | 98.5% | 94.5% (94.1 to 94.8) | 74.9% | 81.4% | about 46 s |

Validation went up 0.7 points. Shift-val went up 0.3, which is inside the seed spread: the two
ranges overlap. The errors moved rather than shrank. Muscle recall fell 7 points and stroma rose
3, so the 128-pixel model calls more muscle "stroma" instead of the other way round. Each run
cost 4.5x the time (about 70 minutes on a T4) and 11.4 GB of memory.

Resolution helped until the fiber shape was visible, and 64 pixels already shows it. The 64-pixel
model stays the final model, and final test was not scored for 128 pixels.

## What carried over

- Validation from the same pool as training only tells you about more of the same. Build a
  held-out set that looks like where the model will be used, and score the final one once.
- Run several seeds before believing a gap, especially on shifted data.
- When accuracy stalls, look at what the model learned. Here it was stain color, and the fix was
  data (resolution), not model size.

## Run it yourself

Everything above runs on a laptop. `scripts/stage3_cnn.py` picks a CUDA (NVIDIA) GPU, then an
Apple GPU (MPS), then CPU. A 64-pixel run is 60 epochs at about 10 to 13 seconds each on a GPU;
CPU is several times slower. The AWS Batch setup in `infra/aws` is optional and bills real money.
