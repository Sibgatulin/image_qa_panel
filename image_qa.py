import panel as pn
import holoviews as hv
from pathlib import Path
from functools import partial
from typing import Optional

# some of the sizing parameters, did not come up with a better place 🤷
N_UNC = 30
N_CAT = 10


class Server:
    """ Define the logic of sorting the filenames """

    SOURCE = "uncategorised"  # the name of the uncategorised store

    def __init__(
        self, files: dict[str, Path], categories: list[str], image_pipe
    ) -> None:
        self._filename_map = files  # used to load images
        self.filenames = list(files.keys())  # presented names
        self.stores = {
            cat: [] for cat in categories
        }  # lists holding categorised filenames
        self.stores[
            self.SOURCE
        ] = self.filenames  # list holding uncategorised filenames
        self.current_filename = None  # once a filename is selected it is held here...
        self._current_source = (
            None  # ...and removed immediately from the corresponding list
        )
        self.pipe = image_pipe  # backdoor into the visualisation
        # not sure if to run self.select(self.SOURCE) here to initialise the stage

    def show(self, data: str) -> hv.RGB:
        """ Function used to create hv.DynamicMap """
        if data is None:
            # The case at the initialisation of client
            return hv.RGB([])
        filepath = str(self._filename_map[data])
        return hv.RGB.load_image(filepath)

    def select(self, store: str, filename: Optional[str] = None) -> None:
        """ Logic of selection from any list (categorised or not) """
        # If selection interrupts categorisation, the current filename
        # needs to be returned to the source store
        if self.current_filename is not None:
            self.stash_current()

        # Newly selected needs to be removed from the queried source
        # Two options possible:
        # After categorisation an image is requested
        # (practically only from the uncategorised source)
        if filename is None:
            # pop closest
            try:
                filename = self.stores[store].pop(0)  # the item is removed
            # automatic query of the next image throws IndexError
            # once self.SOURCE is exhorted
            except IndexError:
                pass
        # Or a specific image from a specific list was selected
        else:
            # remove by name manually
            self.stores[store].remove(filename)

        # Update the info and push
        self.current_filename = filename
        self._current_source = store
        self.pipe.send(filename)

    def stash_current(self):
        """ Return the current image to the list it came from """
        self.stores[self._current_source].append(
            self.current_filename
        )  # or rather prepend?
        # indicate that the stage is free
        self.current_filename = None

    def categorise(self, target_store: str):
        """Once target category is selected place the image there
        and prepare the next
        """
        # Cannot categorise if nothing selected. Should not happen, but will
        # if .select(self.SOURCE) not called after __init__ TODO: improve
        assert self.current_filename is not None, "what'ya categorising there?"
        # Send this out
        self.stores[target_store].append(self.current_filename)
        # Prep the next
        self.current_filename = (
            None  # clear the traces of categorised so that it is not stashed
        )
        self.select(self.SOURCE)


class Client:
    """Define the layout of the panel and add all necessary callbacks.
    Badly needs to somehow ensure things are sized appropriately
    or a convenient interface for it is exposed (it's is not yet at all)
    """

    def __init__(self, server):
        self.server = server
        # init the stage with the first image
        # (could be done in Server().__init__ actually)
        self.server.select(self.server.SOURCE)

        self.n_total = len(server.filenames)  # for progress bar
        self.target_catetories = [
            cat for cat in server.stores if cat != server.SOURCE
        ]  # RHS
        self.dmap = hv.DynamicMap(server.show, streams=[server.pipe]).opts(
            width=600, height=600
        )  # adjust the .opts, maybe expose **kwargs to __init__

        # Init all of the selection widgets, left and right
        self.select = {
            cat: pn.widgets.Select(name=cat, options=server.stores[cat], size=N_CAT)
            for cat in server.stores
        }
        # LHS selection
        self.select[server.SOURCE].options = server.filenames
        self.select[server.SOURCE].size = N_UNC
        # Attach callbacks to each selection
        for cat in server.stores:
            callback = partial(self.select_filename, source_category=cat)
            self.select[cat].param.watch(callback, ["value"])

        # Init buttons and add callbacks
        self.buttons = {
            cat: pn.widgets.Button(name=cat) for cat in self.target_catetories
        }
        for cat in self.target_catetories:
            callback = partial(self.categorise, target_category=cat)
            self.buttons[cat].on_click(callback)

        # the following is updated manually in select_filename and categorise
        # maybe it is possible to attach a callback to listen to the change
        # in self.server.current_filename 🤔
        self.info = pn.widgets.StaticText(value=self.server.current_filename)
        self.pbar = pn.widgets.Progress(value=0, name="Progress", width=100)

    def select_filename(self, event, source_category: str):
        """ Thin wrapper around server.select which connects to a given pn.Select """
        self.server.select(source_category, filename=self.select[source_category].value)
        # update the info
        self.info.value = self.server.current_filename

        # THIS fails the :( Such update does not trigger the widget to be redrawn
        # and the options are not changed unless the cell is rerun
        self.select[source_category].options = self.server.stores[source_category]

    def categorise(self, event, target_category: str):
        """ Thin wrapper around server.categorise """
        self.server.categorise(target_category)

        # TODO: fix the indexing here, something is off by one at the end
        self.pbar.value = int(
            (self.n_total - len(self.server.stores[self.server.SOURCE]))
            / self.n_total
            * 100
        )
        if self.server.stores[self.server.SOURCE]:  # not exhausted
            self.info.value = self.server.current_filename
        else:
            self.info.value = "done here"

        # THIS fails too :( (See self.select_filename)
        self.select[target_category].options = self.server.stores[target_category]

    @property
    def layout(self):
        """ Draw the actual panel """
        return pn.Row(
            self.select[self.server.SOURCE],
            pn.Column(
                pn.Row(self.info, self.pbar),
                pn.Row(*tuple(self.buttons.values())),
                self.dmap,
            ),
            pn.Column(*(self.select[c] for c in self.target_catetories)),
        )
