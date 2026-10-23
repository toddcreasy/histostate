"""Draw the README diagrams into docs/.

- architecture.svg: where training runs, the data splits, and the quality checks
- model.svg: the 64-pixel CNN, block by block

Each box has a hover note and links to its docs or source when the SVG is opened in a browser.

Run: uv run python scripts/make_diagrams.py [--out docs]
"""

import argparse
import html
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, default=Path("docs"))
OUT = parser.parse_args().out
STYLE = {
    "ml": ("#F1ECFB", "#7A57C9", ""),
    "compute": ("#FFF4E5", "#E0862B", ""),
    "data": ("#E7F3EC", "#2F8F5B", ""),
    "ops": ("#EEF1F5", "#6B7A8C", ""),
    "outside": ("#FFFFFF", "#8A8F98", ' stroke-dasharray="6 4"'),
}
REPO = "https://github.com/toddcreasy/histostate/blob/main/"
WALK = REPO + "docs/walkthrough.md"
FONT = "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
CSS = (
    ".t{fill:#1F2933}.s{fill:#52606D;font-size:11px}"
    ".g{fill:#3E4C59;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}"
    ".e{fill:#3E4C59;font-size:10.5px}"
    "a:hover rect.n{stroke-width:2.5}g.h:hover rect.n{stroke-width:2.5}"
)
ARROW = (
    '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#3E4C59"/></marker></defs>'
)


def esc(text):
    return html.escape(text, quote=True)


def header(width, height, title, desc):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f"<title>{esc(title)}</title>",
        f"<desc>{esc(desc)}</desc>",
        ARROW,
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        f"<style>{CSS}</style>",
    ]


def panel(x, y, w, h, label, note):
    return (
        f'<g><title>{esc(note)}</title><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
        f'fill="#FAFBFC" stroke="#CBD2D9" stroke-width="1"/>'
        f'<text x="{x + 14}" y="{y + 20}" class="g">{esc(label)}</text></g>'
    )


def node(x, y, w, h, kind, name, sub, note, link=None):
    fill, stroke, dash = STYLE[kind]
    cx = x + w / 2
    body = (
        f"<title>{esc(note)}</title>"
        f'<rect class="n" x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"{dash}/>'
        f'<text x="{cx}" y="{y + h / 2 - 4}" text-anchor="middle" class="t" font-size="13" '
        f'font-weight="700">{esc(name)}</text>'
        f'<text x="{cx}" y="{y + h / 2 + 13}" text-anchor="middle" class="s">{esc(sub)}</text>'
    )
    if link:
        return f'<a xlink:href="{esc(link)}" href="{esc(link)}" target="_blank">{body}</a>'
    return f'<g class="h">{body}</g>'


def arrow(points, label="", note="", lx=None, ly=None, anchor="start"):
    pts = " ".join(f"{x},{y}" for x, y in points)
    out = f"<g>{f'<title>{esc(note)}</title>' if note else ''}"
    out += (
        f'<polyline points="{pts}" fill="none" stroke="#3E4C59" stroke-width="1.5" '
        f'marker-end="url(#arr)"/>'
    )
    if label:
        out += f'<text x="{lx}" y="{ly}" class="e" text-anchor="{anchor}">{esc(label)}</text>'
    return out + "</g>"


# Architecture: laptop, AWS, data and evaluation, quality checks.
W, H = 1240, 880
LL, LR, AL, AR, NW = 70, 340, 670, 950, 220
R = [80, 190, 300, 400]
NH = 56
mid = [r + NH // 2 for r in R]
s = header(
    W,
    H,
    "histostate: how the tissue classifier is trained and checked",
    "Training runs on a laptop or, for sweeps, as AWS Batch jobs launched by Nextflow. "
    "PathMNIST comes from Zenodo; the test set from a second clinical center is split into "
    "shift-val for tuning and a final test scored once.",
)
s.append('<text x="40" y="26" class="t" font-size="15" font-weight="700">histostate</text>')
s.append(
    '<text x="130" y="26" class="s">Dashed boxes are outside AWS. '
    "Open the SVG on its own and hover a box for what it does and why.</text>"
)
s.append(panel(40, 40, 560, 440, "Laptop", "Every stage runs here. AWS is only for sweeps."))
s.append(
    panel(
        640,
        40,
        560,
        440,
        "AWS (optional, for sweeps)",
        "One stack in us-east-1, deployed with the CDK. Billed only while jobs run.",
    )
)
s.append(
    panel(
        40,
        500,
        1160,
        230,
        "Data and evaluation",
        "Where the tiles come from and which split answers which question.",
    )
)
s.append(panel(40, 750, 1160, 110, "Quality checks", "What runs before code reaches main."))

s += [
    node(
        LL,
        R[0],
        NW,
        NH,
        "ml",
        "uv run stage3_cnn.py",
        "MPS, CUDA, or CPU",
        "Trains the CNN locally. Picks an NVIDIA GPU, then the Apple GPU (MPS), then CPU. A "
        "64-pixel run is 60 epochs at about 12 s each on an M-series Mac.",
        "https://pytorch.org/docs/stable/notes/mps.html",
    ),
    node(
        LL,
        R[1],
        NW,
        NH,
        "ml",
        "histostate ask",
        "tissue type + confidence",
        "The command-line tool: resizes an image to the model's tile size, applies the saved "
        "training mean and spread, and prints the top three tissue types with probabilities.",
        REPO + "src/histostate/ask.py",
    ),
    node(
        LL,
        R[2],
        NW,
        NH,
        "ml",
        "inspect_cnn.py",
        "filters and activations",
        "Saves the learned filters, the activation maps for example tiles, and the tiles that "
        "most excite the strongest stroma/muscle feature. This is how the stain shortcut was "
        "found.",
        REPO + "scripts/inspect_cnn.py",
    ),
    node(
        LL,
        R[3],
        NW,
        NH,
        "ml",
        "evaluate_test.py",
        "final test, once per model",
        "Scores a saved model on validation and on the final test half. Run once per chosen "
        "model; tuning against it would turn it into another validation set.",
        REPO + "scripts/evaluate_test.py",
    ),
    node(
        LR,
        R[0],
        NW,
        NH,
        "ops",
        "nextflow run main.nf",
        "one job per jitter and seed",
        "Turns a sweep such as --jitters 0.3,0.5 --seeds 1,2 into one AWS Batch job per pair, "
        "stages files through S3, retries jobs whose Spot instance is reclaimed, and records time "
        "and memory per job.",
        "https://www.nextflow.io/docs/latest/aws.html",
    ),
    node(
        LR,
        R[1],
        NW,
        NH,
        "ops",
        "docker buildx",
        "linux/amd64 training image",
        "Packages the code and the locked dependencies from uv.lock into one image. The PyTorch "
        "wheels carry the CUDA libraries, so a plain python:3.14-slim base is enough.",
        "https://docs.docker.com/build/",
    ),
    node(
        LR,
        R[2],
        NW,
        NH,
        "ops",
        "cdk deploy",
        "infra/aws, in Python",
        "The AWS CDK describes the stack in Python, with tests, and deploys it through "
        "CloudFormation in one command.",
        "https://docs.aws.amazon.com/cdk/v2/guide/home.html",
    ),
    node(
        LR,
        R[3],
        NW,
        NH,
        "data",
        "models/",
        "checkpoints and logs",
        "Trained weights plus the training mean and spread, the tile size, and the block count, "
        "so ask and evaluate_test rebuild the same model. Not committed to git.",
        "https://pytorch.org/docs/stable/notes/serialization.html",
    ),
    node(
        AL,
        R[0],
        NW,
        NH,
        "compute",
        "AWS Batch",
        "GPU Spot, GPU on-demand, CPU",
        "Three job queues. Batch starts an EC2 instance for each job and scales back to zero "
        "when the queue is empty, so idle time costs nothing.",
        "https://docs.aws.amazon.com/batch/latest/userguide/what-is-batch.html",
    ),
    node(
        AR,
        R[0],
        NW,
        NH,
        "compute",
        "EC2, one per job",
        "g4dn / g5 GPU, c6i / c7i / m6i",
        "GPU jobs run on g4dn.xlarge (NVIDIA T4) or g5.xlarge (A10G); CPU jobs on 8 vCPU c6i, "
        "c7i, or m6i instances. Each job pulls the image and downloads PathMNIST from Zenodo. "
        "Spot reclaimed both GPU instances mid-run once, so the 64-pixel runs used on-demand.",
        "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
    ),
    node(
        AR,
        R[1],
        NW,
        NH,
        "ops",
        "ECR",
        "training image",
        "Private registry for the training image. Batch instances pull it with their own IAM "
        "role, so no registry login lives on the instance.",
        "https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html",
    ),
    node(
        AL,
        R[2],
        NW,
        NH,
        "ops",
        "CloudFormation",
        "HistostateBatchStack",
        "Creates the compute environments, job queues, launch templates, and S3 bucket from "
        "the CDK app. Uses the account's default VPC.",
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html",
    ),
    node(
        AR,
        R[3],
        NW,
        NH,
        "data",
        "S3",
        "work/ and results/",
        "Nextflow's working files under work/, deleted after 30 days, and the checkpoints and "
        "logs under results/. Encrypted, public access blocked.",
        "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
    ),
]
s += [
    arrow([(LR + NW, mid[0]), (AL, mid[0])], "submit jobs", "", LR + NW + 12, mid[0] - 6),
    arrow([(AL + NW, mid[0]), (AR, mid[0])], "start", "", AL + NW + 8, mid[0] - 6),
    arrow([(LR + NW, mid[1]), (AR, mid[1])], "push image", "", LR + NW + 12, mid[1] - 6),
    arrow([(AR + NW / 2, R[1]), (AR + NW / 2, R[0] + NH)], "pull", "", AR + NW / 2 + 6, R[1] - 16),
    arrow([(LR + NW, mid[2]), (AL, mid[2])], "deploy", "", LR + NW + 12, mid[2] - 6),
    arrow(
        [(AR + NW, mid[0]), (AR + NW + 15, mid[0]), (AR + NW + 15, mid[3]), (AR + NW, mid[3])],
        "checkpoint + log",
        "",
        AR + NW + 10,
        (mid[0] + mid[3]) / 2,
        "end",
    ),
    arrow([(AR, mid[3]), (LR + NW, mid[3])], "aws s3 sync", "", AL + 10, mid[3] - 6),
    arrow([(LR, mid[3]), (LL + NW, mid[3])], "load", "", LL + NW + 8, mid[3] - 6),
]

# Data and evaluation row.
C = [60, 290, 520, 750, 980]
DW, RA, RB = 190, 540, 630
ma, mb = RA + NH // 2, RB + NH // 2
s += [
    node(
        C[0],
        RA,
        DW,
        NH,
        "outside",
        "PathMNIST",
        "Zenodo, 28 / 64 / 128 px",
        "MedMNIST's copy of the colorectal tiles as NumPy files, pre-split. CC BY 4.0.",
        "https://medmnist.com/",
    ),
    node(
        C[1],
        RA,
        DW,
        NH,
        "data",
        "NCT-CRC-HE-100K",
        "train 89,996, val 10,004",
        "Training and validation tiles. Validation is a random slice of the same pool, so it "
        "can't see the staining shift.",
        "https://zenodo.org/records/1214456",
    ),
    node(
        C[1],
        RB,
        DW,
        NH,
        "data",
        "CRC-VAL-HE-7K",
        "second center, 7,180 tiles",
        "The official test set, from a different clinical center with different staining. "
        "split_test cuts it into two stratified halves.",
        "https://zenodo.org/records/1214456",
    ),
    node(
        C[2],
        RA,
        DW,
        NH,
        "ml",
        "Train",
        "augment, jitter, keep best",
        "SGD with gradient clipping and cosine decay; flips, rotations, and color jitter on "
        "training batches; keeps the epoch with the best validation accuracy.",
        REPO + "scripts/stage3_cnn.py",
    ),
    node(
        C[2],
        RB,
        DW,
        NH,
        "data",
        "Shift-val",
        "3,587 tiles, tune on this",
        "Half of the second center's tiles. Every setting is compared here, three seeds each.",
        REPO + "src/histostate/splits.py",
    ),
    node(
        C[3],
        RA,
        DW,
        NH,
        "ml",
        "Compare settings",
        "3 seeds each",
        "A gap counts only when the seed ranges don't overlap. Under shift, seeds disagree "
        "several times more than on validation.",
        WALK + "#8-resolution-or-depth",
    ),
    node(
        C[3],
        RB,
        DW,
        NH,
        "data",
        "Final test",
        "3,593 tiles, score once",
        "The other half. Scored once per chosen model, after every decision is made.",
        WALK + "#6-build-a-validation-set-that-can-see-the-shift",
    ),
    node(
        C[4],
        RA,
        DW,
        NH,
        "ml",
        "Chosen model",
        "64 px: 94.7% final test",
        "64 pixels, 3 conv blocks, 93,193 weights, color jitter 0.3. 94.0% on shift-val and "
        "94.7% on final test; stroma and smooth muscle are still its weakest pair.",
        REPO + "src/histostate/cnn.py",
    ),
    arrow([(C[0] + DW, ma), (C[1], ma)]),
    arrow([(C[0] + DW, ma), (C[0] + DW + 20, ma), (C[0] + DW + 20, mb), (C[1], mb)]),
    arrow([(C[1] + DW, ma), (C[2], ma)]),
    arrow([(C[1] + DW, mb), (C[2], mb)]),
    arrow(
        [
            (C[1] + DW / 2, RB + NH),
            (C[1] + DW / 2, RB + NH + 18),
            (C[3] + DW / 2, RB + NH + 18),
            (C[3] + DW / 2, RB + NH),
        ]
    ),
    arrow([(C[2] + DW, ma), (C[3], ma)]),
    arrow(
        [(C[2] + DW, mb), (C[2] + DW + 20, mb), (C[2] + DW + 20, ma + 12), (C[3], ma + 12)],
    ),
    arrow([(C[3] + DW, ma), (C[4], ma)]),
    arrow(
        [(C[3] + DW, mb), (C[3] + DW + 20, mb), (C[3] + DW + 20, ma + 12), (C[4], ma + 12)],
        "score once",
        "",
        C[3] + DW + 24,
        mb - 6,
    ),
]

# Quality checks row.
RQ = 785
mq = RQ + NH // 2
s += [
    node(
        C[0],
        RQ,
        DW,
        NH,
        "ops",
        "pre-commit",
        "ruff before each commit",
        "Lint and format run before a commit lands.",
        "https://pre-commit.com/",
    ),
    node(
        C[1],
        RQ,
        DW,
        NH,
        "outside",
        "GitHub",
        "pull request to main",
        "main is protected: every change arrives as a pull request and is squash-merged.",
        "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/"
        "managing-protected-branches/about-protected-branches",
    ),
    node(
        C[2],
        RQ,
        DW,
        NH,
        "ops",
        "GitHub Actions",
        "uv sync --locked, ruff, pytest",
        "CI on every pull request. --locked fails if pyproject.toml and uv.lock disagree.",
        "https://docs.github.com/actions",
    ),
    node(
        C[3],
        RQ,
        DW,
        NH,
        "ops",
        "pytest",
        "math and shapes, no network",
        "Hand-written softmax, gradients, and convolutions checked against PyTorch, plus "
        "augmentation, splits, the model shapes, and the ask command.",
        "https://docs.pytest.org/en/stable/",
    ),
    arrow([(C[0] + DW, mq), (C[1], mq)]),
    arrow([(C[1] + DW, mq), (C[2], mq)]),
    arrow([(C[2] + DW, mq), (C[3], mq)]),
]
s.append("</svg>")
(OUT / "architecture.svg").write_text("\n".join(s) + "\n")

# Model: the 64-pixel CNN, left to right.
W, H = 1240, 170
m = header(W, H, "The 64-pixel CNN", "Three conv blocks, then one linear layer. 93,193 weights.")
m.append('<text x="40" y="26" class="t" font-size="15" font-weight="700">The model</text>')
m.append(
    f'<text x="140" y="26" class="s"><a xlink:href="{REPO}src/histostate/cnn.py" '
    f'href="{REPO}src/histostate/cnn.py" target="_blank"><tspan text-decoration="underline">'
    "src/histostate/cnn.py</tspan></a>, 64-pixel version. 93,193 weights.</text>"
)
boxes = [
    (
        "data",
        "Tile",
        "3 x 64 x 64",
        "Red, green, and blue, each scaled by the training set's mean and spread.",
        REPO + "scripts/stage3_cnn.py",
    ),
    (
        "ml",
        "Block 1",
        "conv 3x3, 32 filters",
        "32 filters, each a 3x3 pattern over the three colors, slid across the tile. ReLU keeps "
        "positive responses; max pool halves the width and height.",
        "https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html",
    ),
    (
        "ml",
        "Block 2",
        "conv 3x3, 64 filters",
        "Combines first-layer patterns. Each output now sees an 8x8 patch of the tile.",
        "https://pytorch.org/docs/stable/generated/torch.nn.MaxPool2d.html",
    ),
    (
        "ml",
        "Block 3",
        "conv 3x3, 64 filters",
        "Each output sees an 18x18 patch, long enough to span a muscle fiber. The 28-pixel model "
        "stops after block 2.",
        WALK + "#8-resolution-or-depth",
    ),
    (
        "ml",
        "Linear",
        "4,096 to 9",
        "One score per tissue class from the 64 x 8 x 8 feature grid.",
        "https://pytorch.org/docs/stable/generated/torch.nn.Linear.html",
    ),
    (
        "data",
        "Softmax",
        "9 probabilities",
        "Turns scores into probabilities that sum to 1. Training lowers cross-entropy, which "
        "punishes confident wrong answers hardest.",
        REPO + "src/histostate/softmax.py",
    ),
]
shapes = ["", "32 x 32 x 32", "64 x 16 x 16", "64 x 8 x 8", "", ""]
BW, gap, y = 170, 36, 70
x0 = (W - (6 * BW + 5 * gap)) / 2
for i, (kind, name, sub, note, link) in enumerate(boxes):
    x = x0 + i * (BW + gap)
    m.append(node(x, y, BW, NH, kind, name, sub, note, link))
    if i:
        m.append(arrow([(x - gap, y + NH / 2), (x, y + NH / 2)]))
    if shapes[i]:
        m.append(
            f'<text x="{x + BW / 2}" y="{y + NH + 22}" text-anchor="middle" class="e">'
            f"out: {shapes[i]}</text>"
        )
m.append("</svg>")
(OUT / "model.svg").write_text("\n".join(m) + "\n")
print("wrote", OUT / "architecture.svg", OUT / "model.svg")
