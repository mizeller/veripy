# IMPORTS
from pathlib import Path
from isort import file
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams.update({
    'axes.titlesize': 'medium', 
    'axes.labelsize': 'small',
    'legend.title_fontsize' : 'small',
    }
)

# import datetime
from utils.atab import Atab

from pprint import pprint
import pandas as pd
from ipdb import set_trace as dbg


from utils.parse_plot_synop_ch import total_score_range, cat_total_score_range
from utils.check_params import check_params



def collect_relevant_files(file_prefix, file_postfix, debug, source_path, parameter):
    """Collect all files corresponding to current parameter in 'corresponding_files_dict'.

    Args:
        file_prefix (str): prefix of files we're looking for (i.e. total_scores)
        file_postfix (str): postfix of files we're looking for (i.e. .dat)
        debug (bool): add debug messages command prompt
        source_path (Path): path to directory, where source files are
        parameter (str): parameter of interest

    Returns:
        dict: dictionary containig all available lead time range (ltr) dataframes for parameter
    """
    # collect the files, corresponding to this parameter in the corresponding files dict.
    # the keys in this dict are the available lead time ranges for the current parameter.
    corresponding_files_dict = {}
    for file_path in source_path.glob(f"{file_prefix}*{parameter}{file_postfix}"):
        if file_path.is_file(): # check, that the corresponding path belongs to a file and not to a sub-directory

            # lt_range = key for corresponding_files_dict
            lt_range = file_path.name[len(file_prefix):len(file_prefix)+5]

            # extract header & dataframe
            header = Atab(file=file_path, sep=" ").header
            df = Atab(file=file_path, sep=" ").data

            # clean df
            df = df.replace(float(header["Missing value code"][0]), np.NaN)

            df.set_index(keys='Score', inplace=True)

            # add information to dict
            corresponding_files_dict[lt_range] = {
                                                    # 'path':file_path,
                                                    'header':header,
                                                    'df':df
                                                }
    if debug:
        print(f"\nFor parameter: {parameter} these files are relevant:")
        pprint(corresponding_files_dict)

    return corresponding_files_dict


# enter directory / read total_scores files / call plotting pipeline
def _total_scores_pipeline(
    params_dict,
    plot_scores,
    plot_cat_scores,
    file_prefix,
    file_postfix,
    input_dir,
    output_dir,
    season,
    model_version,
    grid,
    debug,
) -> None:
    """Read all ```ATAB``` files that are present in: data_dir/season/model_version/<file_prefix><...><file_postfix>
        Extract relevant information (parameters/scores) from these files into a dataframe.
        Rows --> Scores | Columns --> Stations | For each parameter, a separate station_scores File exists.


    Args:
        parameters (list): parameters, for which plots should be generated (i.e. CLCT, DD_10M, FF_10M, PMSL,...). part of file name
        file_prefix (str): prefix of files (i.e. time_scores)
        file_postfix (str): postfix of files (i.e. '.dat')
        input_dir (str): directory to seasons (i.e. /scratch/osm/movero/wd)
        output_dir (str): output directory (i.e. plots/)
        season (str): season of interest (i.e. 2021s4/)
        model_version (str): model_version of interest (i.e. C-1E_ch)
        scores (list): list of scores, for which plots should be generated
        debug (bool): print further comments & debug statements
    """
    print(f"\n--- initialising total scores pipeline")
    print(f"--- initialising total scores parsing pipeline")

    source_path = Path(f"{input_dir}/{season}/{model_version}")
    for parameter in params_dict:
        corresponding_files_dict = collect_relevant_files(file_prefix, file_postfix, debug, source_path, parameter)
        # pass dict to plotting pipeline
        _generate_total_scores_plot(
            data=corresponding_files_dict,
            parameter=parameter,
            plot_scores=plot_scores,
            plot_cat_scores=plot_cat_scores,
            output_dir=output_dir,
            grid=grid,
            debug=debug,
        )

    
    return
    


############################################################################################################################
######################################### PLOTTING PIPELINE FOR TOTAL SCORES PLOTS #########################################
############################################################################################################################

def _set_ylim(param, score, ax, debug):
    # define limits for yaxis if available
    regular_param = (param, "min") in total_score_range.columns
    regular_score = score in total_score_range.index

    if regular_param and regular_score:
        lower_bound = total_score_range[param]["min"].loc[score]
        upper_bound = total_score_range[param]["max"].loc[score]
        if debug:
            print(
                f"found limits for {param}/{score} --> {lower_bound}/{upper_bound}"
        )
        if lower_bound != upper_bound:
            ax.set_ylim(lower_bound, upper_bound)
    return

def _customise_ax(parameter, score, x_ticks,grid, ax):
    """Apply cosmetics to current ax.

    Args:
        parameter (str): current parameter
        score (str): current score
        x_ticks (list): list of x-ticks labels (lead time ranges, as strings)
        grid (bool): add grid to ax
        ax (Axes): current ax
    """
    if grid:
        ax.grid(which='major', color='#DDDDDD', linewidth=0.8)
        ax.grid(which='minor', color='#EEEEEE', linestyle=':', linewidth=0.5)
        ax.minorticks_on()

    ax.tick_params(axis='both', which='major', labelsize=8)
    ax.tick_params(axis='both', which='minor', labelsize=6)
    ax.set_title(f"{parameter}: {score}")
    ax.set_xlabel(f"Lead-Time Range (h)")
    ax.legend(fontsize=6)
    ax.set_xticks(range(len(x_ticks)), x_ticks)
    return

def _clear_empty_axes(subplot_axes, idx):
    # remove empty ``axes`` instances
    i = 1
    while (idx%4+i) < 4:
        ax = subplot_axes[idx%4+i]
        ax.axis('off')
        i += 1
    return

def _save_figure(output_dir, filename):
    print(f"saving: {output_dir}/{filename[:-1]}.png")
    plt.savefig(f"{output_dir}/{filename[:-1]}.png")
    plt.clf()
    return


def _generate_total_scores_plot(
    data,
    parameter,
    plot_scores,
    plot_cat_scores,
    output_dir,
    grid,
    debug,
):
    """Generate Total Scores Plot."""
    print(f"\n--- initialising total scores plotting pipeline")

    # get correct parameter
    param = check_params(param=parameter, verbose=debug)

    # check (&create) output directory for total scores plots
    output_dir = f"{output_dir}/total_scores"
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # create 2x2 subplot grid
    fig, ((ax0, ax1),(ax2, ax3)) = plt.subplots(nrows=2, ncols=2, tight_layout=True, figsize=(10, 10), dpi=200)
    subplot_axes = {0:ax0, 1:ax1, 2:ax2, 3:ax3}

    # ltr_unsorted  ->  unsorted lead time ranges 
    # ltr_sorted    ->  sorted lead time ranges (used for x-tick-labels later on )
    
    ltr_unsorted, ltr_sorted = list(data.keys()), []
    ltr_start_times_sorted = sorted([int(lt.split('-')[0]) for lt in ltr_unsorted])
    for idx, ltr_start in enumerate(ltr_start_times_sorted):
        for ltr in ltr_unsorted:
            if ltr.startswith(str(ltr_start).zfill(2)):
                ltr_sorted.insert(idx, ltr)
    
    # re-name & create x_int list, s.t. np.arrays are plottet against each other
    x_ticks = ltr_sorted
    x_int = list(range(len(ltr_sorted)))


    # extract header from data & create title
    header = data[ltr_sorted[-1]]['header']    
    footer = f"Model: {header['Model version'][0]} | Period: {header['Start time'][0]} - {header['End time'][0]} | © MeteoSwiss"

    # initialise filename
    filename = 'total_scores_'

    ############################################################################
    ##################### REGULAR SCORES PLOTTING PIPELINE #####################
    ############################################################################
    regular_scores = plot_scores.split(',')
    for idx, score in enumerate(regular_scores):
        if debug: 
            print(f"--- plotting:\t{param}/{score}")
       
        multiplt=False

        # save filled figure & re-set necessary for next iteration
        if idx > 0 and idx%4==0:
            # add title to figure
            plt.suptitle(
                footer,
                horizontalalignment="center",
                verticalalignment="top",
                fontdict={
                    "size": 6,
                    "color": "k",
                },
            )
            _save_figure(output_dir=output_dir, filename=filename)
            fig, ((ax0, ax1),(ax2, ax3)) = plt.subplots(nrows=2, ncols=2, tight_layout=True)
            subplot_axes = {0:ax0, 1:ax1, 2:ax2, 3:ax3}
            # reset filename
            filename = 'total_scores_'

        # get ax, to add plot to
        ax = subplot_axes[idx%4]

        # plot two scores on one sub-plot
        if '/' in score:
            multiplt = True
            scores = score.split('/')
            filename += f"{scores[0]}_{scores[1]}_"
            _set_ylim(param=param, score=scores[0], ax=ax, debug=debug)
            
            # get y0, y1 from dfs
            y0, y1 = [], []
            for ltr in ltr_sorted:
                y0.append(data[ltr]['df']['Total'].loc[scores[0]])
                y1.append(data[ltr]['df']['Total'].loc[scores[1]])
            
            # plot y0, y1
            ax.plot(x_int, y0, color="red", linestyle="-", marker='^', fillstyle='none', label=f"{scores[0].upper()}")
            ax.plot(x_int, y1, color="k", linestyle="-", marker='D', fillstyle='none', label=f"{scores[1].upper()}")
            
        # plot single score on sub-plot
        if not multiplt:
            filename += f"{score}_"
            _set_ylim(param=param, score=score, ax=ax, debug=debug)
            
            y = []
            # extract y from different dfs
            for ltr in ltr_sorted:
                ltr_score = data[ltr]['df']['Total'].loc[score]
                y.append(ltr_score)

            ax.plot(x_int, y, color="k", linestyle="-", marker='D', fillstyle='none', label=f"{score.upper()}")
        
        # customise grid, title, xticks, legend of current ax
        _customise_ax(parameter=param, score=score, x_ticks=x_ticks, grid=True, ax=ax)

        # save figure, if this is the last score
        if idx == len(regular_scores)-1:
            # add title to figure
            plt.suptitle(
                footer,
                horizontalalignment="center",
                verticalalignment="top",
                fontdict={
                    "size": 6,
                    "color": "k",
                },
            )
            # clear empty subplots
            _clear_empty_axes(subplot_axes=subplot_axes, idx=idx)
            # save & clear figure
            _save_figure(output_dir=output_dir, filename=filename)

    ############################################################################
    ################### CATEGORICAL SCORES PLOTTING PIPELINE ###################
    # remark: include thresholds for categorical scores
    ############################################################################
    # TODO





    return

