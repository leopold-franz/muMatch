import os
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import yaml

from .correspondence.match import Match
from .preprocessing.deep_functional_maps import optimise_signatures
from .preprocessing.preprocess import batch_preprocess
from .shape_analysis import shape_alignment as align
from .shape_analysis.statistical_shape_analysis import (
    clustering_analysis,
    collection_deviation,
)


def mesh_correspondence(
    data_dir: str,
    match_dir: str,
    mesh_pairs: List[Tuple[str, str]],
    correspondence_config: Dict,
) -> pd.DataFrame:
    """
    Here we compute the actual correspondences between input meshes. A functor matching_functional is created and a match between a pair of meshes is computed by calling it with their respective filenames. There are two ways of doing this:
    * A minimal way is to identify a template mesh and compute the correspondences between this and all other meshes (this is what is done in the code block below).
    * A more advanced way is to compute all pairwise correspondences. This will take much longer, but then improvement schemes can be used subsequently to increase the qualtity of the correspondences.

    Parameters
    ----------
    data_dir : str
        Path to data directory
    match_dir : str
        Path to directory to save match results into
    mesh_pairs : List[Tuple[str, str]]
        Pair of mesh file names in data directory to compare.
    correspondence_config : Dict
        Dictionary of correspondence settings

    Returns
    -------
    pd.DataFrame
        geodesic distortion dataframe of all matches
    """
    if not os.path.exists(match_dir):
        os.makedirs(match_dir)

    matching_functional = Match(
        dir_in=data_dir,
        dir_out=match_dir,
        config=correspondence_config,
        display_result=False,
    )
    prev_files = list({corr[0] for corr in mesh_pairs})
    curr_files = list({corr[1] for corr in mesh_pairs})
    geodesic_distortions = pd.DataFrame(
        0, index=prev_files, columns=curr_files
    )
    for correspondence in mesh_pairs:
        mesh_a, mesh_b = correspondence
        geodesic_distortions.loc[mesh_a, mesh_b] = matching_functional(
            mesh_a, mesh_b
        )
    geodesic_distortions.to_csv(
        os.path.join(match_dir, "geodesic_distortions.csv")
    )

    return geodesic_distortions


def shape_analysis(data_dir, match_dir, dataset_id):
    """
    This is an example of the kind of analysis one can do once correspondences have been established.
    * The meshes are aligned to yield a set of aligned point clouds (whose points have also been placed in a one-to-one correspondence).
    * A procrustes analysis is done to retrieve the differences (deviations) at each point from the average mesh.
    * Finally, these deviations are fed into a function to extract the principal components of the deviations and the resulting two first PC are plotted.

    Parameters
    ----------
    data_dir : str
        Path to data directory
    match_dir : str
        Path to match directory
    dataset_id : str
        Name of the dataset being analysed. Only used to better label plots and analysis results.

    Returns
    -------
        None
    """
    names, point_clouds = align.process_directory(
        data_dir, match_dir, display=True
    )
    deviations = collection_deviation(point_clouds, iterations=10)

    raw_dir = os.path.join(data_dir, "raw")
    raw_files = [str(path.stem) for path in Path(raw_dir).glob("*.ply")]

    classes = raw_files
    clustering_analysis(classes, deviations, variant=dataset_id)


def run_microMatch(
    data_dir: str,
    mesh_pairs: List[Tuple[str, str]],
    dataset_id: str = "Dataset",
    use_deep_learning: bool = True,
    perform_shape_analysis: bool = True,
):
    """
    This runs the µMatch Pipeline from start to end and calculates the shape correspondences for a set of meshes and
    mesh correspondences.

    Parameters
    ----------
    data_dir : str
        Path to data directory where the set of input meshes are stored.
    mesh_pairs: List[Tuple[str, str]]
        List of tuples. Each tuple contains the names of two meshes in the mesh dataset to compare. The names of the
        meshes are the file names (excluding file extensions) situated in the data_dir.
        For example: [("Q02", "Q03"), ("Q03", "Q04")]
    dataset_id : str
        Mesh dataset name
    use_deep_learning: bool
        If set to true improve signature maps using deep learning.
    perform_shape_analysis: bool
        Runs shape analysis at the end of the pipeline if set to true.

    Returns
    -------
        None
    """

    # Load Parameter file
    # If you wish to experiment with any of the default parameters (e.g., number of mesh vertices),
    # open the parameters.yml file and adjust the relevant parameter values.
    with open("parameters.yml") as file:
        config = yaml.safe_load(file)

    # Preprocessing
    # * raw_dir should point to the folder containing the meshes that we wish to process.
    # * data_dir should point to where we want the processed data to be stored for later use.
    raw_dir = os.path.join(data_dir, "raw")

    data_dir = os.path.join(data_dir, "processed_data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    batch_preprocess(raw_dir, data_dir, config["preprocessing"])

    # Deep functional maps
    # Note: This step is optional and the pipeline can run successfully without it.
    # To improve the signature functions using deep functional maps, set the parameter "use_deep_learning" to True.
    # To ignore this step, set the parameter "use_deep_learning" to False.
    if use_deep_learning:
        checkpoint_dir = os.path.join(data_dir, "checkpoints")
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        optimise_signatures.process_directory(
            data_dir=data_dir,
            checkpoint_dir=checkpoint_dir,
            config=config["preprocessing"],
            mesh_type=dataset_id,
        )

    # Mesh correspondence
    match_dir = os.path.join(data_dir, "match_results")
    geodesic_distortions = mesh_correspondence(
        data_dir, match_dir, mesh_pairs, config["correspondence"]
    )

    # Shape analysis
    if perform_shape_analysis:
        shape_analysis(
            data_dir=data_dir, match_dir=match_dir, dataset_id=dataset_id
        )

    return geodesic_distortions


def run_micromatch_test():
    """
    Test microMatch pipeline with test data.

    Returns
    -------
        None
    """
    example_data_dir = Path(__file__).resolve().parent.parent / "example_data"

    run_microMatch(
        data_dir=str(example_data_dir),
        mesh_pairs=[("Q02", "Q03"), ("Q03", "Q04")],
        dataset_id="Teeth_dataset",
    )
