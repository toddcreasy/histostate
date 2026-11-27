import { Help } from "./help";

// The help notes on the home page. Facts come from the README and docs/walkthrough.md.

const REPO = "https://github.com/toddcreasy/histostate";

const Head = ({ children }: { children: React.ReactNode }) => (
  <h3 className="mt-1 text-xs font-semibold tracking-wide text-ink uppercase">{children}</h3>
);

const Link = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <a href={href} target="_blank" rel="noopener noreferrer" className="text-ink underline underline-offset-4">
    {children}
  </a>
);

export function PageHelp() {
  return (
    <Help page title="About histostate" className="ml-3">
      <Head>What it is</Head>
      <p>
        A small CNN (convolutional neural network) that names the tissue type in a colorectal H&amp;E
        (hematoxylin and eosin) tile. I built and trained it from scratch in PyTorch, with no
        pretrained weights, as a way to learn every piece from gradient descent up.
      </p>

      <Head>The data</Head>
      <p>
        PathMNIST, from MedMNIST: 107,180 tiles in nine tissue classes. Training and validation tiles
        come from one clinical center. The test tiles come from a second center, where the staining
        looks different, and the scores here are on those.
      </p>

      <Head>How good it is</Head>
      <p>
        <strong>94.7%</strong> on the final test half from the second center. Stroma (75% recall)
        and smooth muscle (83%) are its main confusion.
      </p>

      <Head>Where to read more</Head>
      <p>
        The <Link href={`${REPO}/blob/main/docs/walkthrough.md`}>walkthrough</Link> tells it stage
        by stage, the <Link href={`${REPO}/blob/main/docs/software.md`}>software list</Link> says
        why each tool was picked, and the <Link href={REPO}>source</Link> is on GitHub.
      </p>
      <p>A learning project, not a medical device. Nothing here is for clinical or diagnostic use.</p>
    </Help>
  );
}

export function ClassifierHelp() {
  return (
    <Help title="Reading the answer" className="ml-2">
      <p>
        Your image is shrunk to <strong>64x64 pixels</strong> the same way{" "}
        <code className="text-ink">histostate ask</code> does it, and the model runs in your browser
        with ONNX Runtime Web. Nothing is uploaded.
      </p>
      <p>
        The tile on the left is exactly what the model sees. The percentages are its probabilities
        for the nine tissues, which always add up to 100%.
      </p>
      <p>
        A high percentage means the model is sure, not that it is right. It always picks one of the
        nine, even for a photo of a cat, and it was trained only on PathMNIST tiles.
      </p>
    </Help>
  );
}
