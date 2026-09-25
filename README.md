# Tensile Manual Builder

This browser app reads raw tensile curves from the provided Bluehill `.id_tens`
layout, overlays specimens, calculates an average force-versus-extension curve,
and exports a product-manual PDF.

## Run in a browser workspace

1. Create a new GitHub repository.
2. Add the three files in this folder: `app.py`, `tens_parser.py`, and
   `requirements.txt`.
3. Create an account at Streamlit Community Cloud, choose the repository, and
   deploy `app.py`.
4. Open the resulting web address and upload an `.id_tens` file.

For company data, deploy only to a company-approved platform. Do not use a
public demo host unless your employer approves uploading the test data there.

## Current support

* Bluehill `.id_tens` files matching the supplied test-file structure.
* Multiple specimens in one file.
* Force (kN) versus extension (mm).
* Full and early-stretch overlay plots.
* Average curve on the common extension range, with a ±1 standard-deviation
  band.
* Product property entry and PDF export.

## Important validation

`.id_tens` is a proprietary Instron format. Before using this for released
reports, compare a few calculated peaks and curves with Bluehill output from
your instrument/software version. If a new layout does not parse, export raw
data to CSV from Bluehill and add that file as a supported import format.
