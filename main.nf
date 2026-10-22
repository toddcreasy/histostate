#!/usr/bin/env nextflow
// histostate: one GPU job per Stage 3 training run, one run per jitter and seed pair.
// Example: nextflow run main.nf -profile aws,gpu --jitters 0.3,0.5 --seeds 1,2
// The cpu or gpu profile sets params.device and the queue; pick one alongside aws.

params.jitters = '0.3'
params.seeds = '0'
params.epochs = 60
params.device = 'cpu'
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
    // Fail in seconds, not after 60 epochs, if a GPU job's container cannot see the GPU.
    def gpu_check = params.device == 'cuda'
        ? "python -c \"import torch; print('GPU:', torch.cuda.get_device_name())\""
        : ''
    """
    ${gpu_check}
    python -u /app/scripts/stage3_cnn.py --device ${params.device} --epochs ${params.epochs} \\
        --jitter ${jitter} --seed ${seed} --save stage3_j${jitter}_s${seed}.pt \\
        | tee stage3_j${jitter}_s${seed}.log
    """
}

workflow {
    jitters = channel.fromList(params.jitters.toString().tokenize(','))
    seeds = channel.fromList(params.seeds.toString().tokenize(','))
    TRAIN(jitters.combine(seeds))
}
