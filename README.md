# Image sorting dashboard

A quick and simple dashboard with holoviews and panel to sort images into
categories.

The logic of sorting is implemented in Server class and seems solid. The
desired interaction between panel elements is defined in Client and it is
lacking. Particularly it was build around idea of filenames moving from one
pn.widget.Select to either of a number of target Select widgets (all callable
and allowing to select an image). Unfortunately, none of the Select areas ever
updates its options so the panel looks a little sorry for itself, yet works.

Perhaps, Client could have been perfectly suitable for a subclass of
param.Parametrized 🤔
