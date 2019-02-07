import os
import json
from six import iteritems, itervalues
import networkx as nx
from collections import OrderedDict
import base64

from openmdao.devtools.html_utils import head_and_body, write_style

try:
    import h5py
except ImportError:
    # Necessary for the file to parse
    h5py = None

from openmdao.core.group import Group
from openmdao.core.problem import Problem
from openmdao.core.implicitcomponent import ImplicitComponent
from openmdao.utils.class_util import overrides_method
from openmdao.utils.general_utils import warn_deprecation, simple_warning
from openmdao.utils.record_util import check_valid_sqlite3_db
from openmdao.utils.mpi import MPI


def _get_tree_dict(system, component_execution_orders, component_execution_index):
    """Get a dictionary representation of the system hierarchy."""
    tree_dict = OrderedDict()
    tree_dict['name'] = system.name
    tree_dict['type'] = 'subsystem'

    if not isinstance(system, Group):
        tree_dict['subsystem_type'] = 'component'
        component_execution_orders[system.pathname] = component_execution_index[0]
        component_execution_index[0] += 1

        children = []
        for typ in ['input', 'output']:
            for ind, abs_name in enumerate(system._var_abs_names[typ]):
                meta = system._var_abs2meta[abs_name]
                name = system._var_abs2prom[typ][abs_name]

                var_dict = OrderedDict()
                var_dict['name'] = name
                if typ == 'input':
                    var_dict['type'] = 'param'
                elif typ == 'output':
                    isimplicit = isinstance(system, ImplicitComponent)
                    var_dict['type'] = 'unknown'
                    var_dict['implicit'] = isimplicit

                var_dict['dtype'] = type(meta['value']).__name__
                children.append(var_dict)
    else:
        tree_dict['subsystem_type'] = 'group'
        children = [_get_tree_dict(s, component_execution_orders, component_execution_index)
                    for s in system._subsystems_myproc]
        if system.comm.size > 1:
            if system._subsystems_myproc:
                sub_comm = system._subsystems_myproc[0].comm
                if sub_comm.rank != 0:
                    children = []
            children_lists = system.comm.allgather(children)

            children = []
            for children_list in children_lists:
                children.extend(children_list)

    if isinstance(system, ImplicitComponent):
        if overrides_method('solve_linear', system, ImplicitComponent):
            tree_dict['linear_solver'] = "solve_linear"
        else:
            tree_dict['linear_solver'] = ""
    else:
        if system.linear_solver:
            tree_dict['linear_solver'] = system.linear_solver.SOLVER
        else:
            tree_dict['linear_solver'] = ""

    if isinstance(system, ImplicitComponent):
        if overrides_method('solve_nonlinear', system, ImplicitComponent):
            tree_dict['nonlinear_solver'] = "solve_nonlinear"
        else:
            tree_dict['nonlinear_solver'] = ""
    else:
        if system.nonlinear_solver:
            tree_dict['nonlinear_solver'] = system.nonlinear_solver.SOLVER
        else:
            tree_dict['nonlinear_solver'] = ""

    tree_dict['children'] = children

    if not tree_dict['name']:
        tree_dict['name'] = 'root'
        tree_dict['type'] = 'root'

    return tree_dict


def _get_viewer_data(data_source):
    """
    Get the data needed by the N2 viewer as a dictionary.

    Parameters
    ----------
    data_source : <Problem> or <Group> or str
        A Problem or Group or case recorder file name containing the model or model data.

    Returns
    -------
    dict
        A dictionary containing information about the model for use by the viewer.
    """
    if isinstance(data_source, Problem):
        root_group = data_source.model
        if not isinstance(root_group, Group):
            simple_warning("The model is not a Group, viewer data is unavailable.")
            return {}

    elif isinstance(data_source, Group):
        if not data_source.pathname:  # root group
            root_group = data_source
        else:
            # this function only makes sense when it is at the root
            return {}

    elif isinstance(data_source, str):
        check_valid_sqlite3_db(data_source)
        import sqlite3
        con = sqlite3.connect(data_source, detect_types=sqlite3.PARSE_DECLTYPES)
        cur = con.cursor()
        cur.execute("SELECT format_version FROM metadata")
        row = cur.fetchone()
        format_version = row[0]

        cur.execute("SELECT model_viewer_data FROM driver_metadata;")
        model_text = cur.fetchone()

        from six import PY2, PY3
        if row is not None:
            if format_version >= 3:
                return json.loads(model_text[0])
            elif format_version in (1, 2):
                if PY2:
                    import cPickle
                    return cPickle.loads(str(model_text[0]))
                if PY3:
                    import pickle
                    return pickle.loads(model_text[0])

    else:
        raise TypeError('_get_viewer_data only accepts Problems, Groups or filenames')

    data_dict = {}
    comp_exec_idx = [0]  # list so pass by ref
    comp_exec_orders = {}
    data_dict['tree'] = _get_tree_dict(root_group, comp_exec_orders, comp_exec_idx)

    connections_list = []

    # sort to make deterministic for testing
    sorted_abs_input2src = OrderedDict(sorted(root_group._conn_global_abs_in2out.items()))
    root_group._conn_global_abs_in2out = sorted_abs_input2src
    G = root_group.compute_sys_graph(comps_only=True)
    scc = nx.strongly_connected_components(G)
    scc_list = [s for s in scc if len(s) > 1]
    for in_abs, out_abs in iteritems(sorted_abs_input2src):
        if out_abs is None:
            continue
        src_subsystem = out_abs.rsplit('.', 1)[0]
        tgt_subsystem = in_abs.rsplit('.', 1)[0]
        src_to_tgt_str = src_subsystem + ' ' + tgt_subsystem

        count = 0
        edges_list = []
        for li in scc_list:
            if src_subsystem in li and tgt_subsystem in li:
                count += 1
                if count > 1:
                    raise ValueError('Count greater than 1')

                exe_tgt = comp_exec_orders[tgt_subsystem]
                exe_src = comp_exec_orders[src_subsystem]
                exe_low = min(exe_tgt, exe_src)
                exe_high = max(exe_tgt, exe_src)

                subg = G.subgraph(n for n in li if exe_low <= comp_exec_orders[n] <= exe_high)
                for edge in subg.edges():
                    edge_str = ' '.join(edge)
                    if edge_str != src_to_tgt_str:
                        edges_list.append(edge_str)

        if edges_list:
            edges_list.sort()  # make deterministic so same .html file will be produced each run
            connections_list.append(OrderedDict([('src', out_abs), ('tgt', in_abs),
                                                 ('cycle_arrows', edges_list)]))
        else:
            connections_list.append(OrderedDict([('src', out_abs), ('tgt', in_abs)]))

    data_dict['connections_list'] = connections_list

    data_dict['abs2prom'] = root_group._var_abs2prom

    return data_dict


def view_tree(*args, **kwargs):
    """
    view_tree was renamed to view_model, but left here for backwards compatibility
    """
    warn_deprecation("view_tree is deprecated. Please switch to view_model.")
    view_model(*args, **kwargs)


def view_model(data_source, outfile='n2.html', show_browser=True, embeddable=False,
               draw_potential_connections=True):
    """
    Generates an HTML file containing a tree viewer.

    Optionally opens a web browser to view the file.

    Parameters
    ----------
    data_source : <Problem> or str
        The Problem or case recorder database containing the model or model data.

    outfile : str, optional
        The name of the final output file

    show_browser : bool, optional
        If True, pop up the system default web browser to view the generated html file.
        Defaults to True.

    embeddable : bool, optional
        If True, gives a single HTML file that doesn't have the <html>, <DOCTYPE>, <body>
        and <head> tags. If False, gives a single, standalone HTML file for viewing.

    draw_potential_connections : bool, optional
        If true, allows connections to be drawn on the N2 that do not currently exist
        in the model. Defaults to True.
    """
    # grab the model viewer data
    model_viewer_data = _get_viewer_data(data_source)
    model_viewer_data = 'var modelData = %s' % json.dumps(model_viewer_data)

    # if MPI is active only display one copy of the viewer
    if MPI and MPI.COMM_WORLD.rank != 0:
        return

    code_dir = os.path.dirname(os.path.abspath(__file__))
    vis_dir = os.path.join(code_dir, "visualization")
    libs_dir = os.path.join(vis_dir, "libs")
    src_dir = os.path.join(vis_dir, "src")
    style_dir = os.path.join(vis_dir, "style")

    # grab the libraries, src and style
    libs = _read_files(('awesomplete', 'd3.v4.min', 'vkBeautify'), libs_dir, 'js')
    src_names = 'constants', 'draw', 'legend', 'modal', 'ptN2', 'search', 'svg'
    srcs = _read_files(src_names, src_dir, 'js')
    styles = _read_files(('awesomplete', 'partition_tree'), style_dir, 'css')
    style_elems = '\n\n'.join([write_style(content=s) for s in itervalues(styles)])

    with open(os.path.join(style_dir, "fontello.woff"), "rb") as f:
        encoded_font = str(base64.b64encode(f.read()).decode("ascii"))

    # grab the index.html
    with open(os.path.join(vis_dir, "index.html"), "r") as f:
        index = f.read()

    # add the necessary HTML tags if we aren't embedding
    if embeddable:
        index = '\n\n'.join([style_elems, index])
    else:
        meta = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
        head = '\n\n'.join([meta, style_elems])
        index = head_and_body(head, index)

    # put all style and JS into index
    index = index.replace('{{fontello}}', encoded_font)

    for k, v in iteritems({'d3': 'd3.v4.min', 'awesomplete': 'awesomplete', 'vk_beautify': 'vkBeautify'}):
        index = index.replace('{{{}_lib}}'.format(k), libs[v])

    for name, code in iteritems(srcs):
        index = index.replace('{{{}_lib}}'.format(name.lower()), code)
    index = index.replace('{{model_data}}', model_viewer_data)
    index = index.replace('{{draw_potential_connections}}', str(draw_potential_connections).lower())

    with open(outfile, 'w') as f:  # write output file
        f.write(index)

    # open it up in the browser
    if show_browser:
        from openmdao.devtools.webview import webview
        webview(outfile)


def _read_files(filenames, directory, extension):
    # Reads files (based on filenames) from a directory with a given extension.
    libs = dict()
    for name in filenames:
        with open(os.path.join(directory, '.'.join([name, extension])), "r") as f:
            libs[name] = f.read()
    return libs
