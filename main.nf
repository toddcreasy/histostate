#!/usr/bin/env nextflow
// histostate: one GPU job per Stage 3 training run, one run per jitter and seed pair.
// Example: nextflow run main.nf -profile aws --jitters 0.3,0.5 --seeds 1,2

params.jitters = '0.3'
params.seeds = '0'
params.epochs = 60
params.outdir = 'results'

process TRAIN {
    tag "jitter ${jitter} seed ${seed}"
    publishDir "${params.outdir}/stage3", mode: 'copy'

    input:
    tuple val(jitter), val(seed)

    output:
    path "stage3_j${jitter}_s${seed}.pt"
    path "stage3_j${jitter}_s${seed}.log"

    script:
    """
    # Fail in seconds, not after 60 CPU-speed epochs, if the container cannot see the GPU.
    python -c "import torch; print('GPU:', torch.cuda.get_device_name())"
    python -u /app/scripts/stage3_cnn.py --device cuda --epochs ${params.epochs} \\
        --jitter ${jitter} --seed ${seed} --save stage3_j${jitter}_s${seed}.pt \\
        | tee stage3_j${jitter}_s${seed}.log
    """
}

workflow {
    jitters = channel.fromList(params.jitters.toString().tokenize(','))
    seeds = channel.fromList(params.seeds.toString().tokenize(','))
    TRAIN(jitters.combine(seeds))
}
