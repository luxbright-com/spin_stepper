A Python interface for the STSPIN stepper motor drivers from STMicroelectronics (ST).

The STSPIN family of stepper motor drives has a lot of really nice built-in functions
that You normally must implement in Python.
Position counter
Advanced commands such as go_to, go_home


This library has been developed and tested using the L6470HTR circuit connected via SPI to
a Raspberry Pi 4 with Raspbian Bookworm.
This will probably work with most circuits in this family, but scaling of some values might need adjustment.

Documentation on the L6470 circuit can be downloaded here: https://www.st.com/en/motor-drivers/l6470.html
SparkFun has developed a really nice board ned AutoDriver for playing with this circuit,
but this product is now retired. https://github.com/sparkfun/L6470-AutoDriver
ST has an evaluation board called EVAL6470H https://www.st.com/en/evaluation-tools/eval6470h.html

This is a fork from the st-spin package https://github.com/m-laniakea/st_spin by eir.
But it has been re-worked from the ground up to be more pythonic and to handle most of the commands.

Our purpose with this library was to solve our internal needs.
We use this for internally developed lab and production equipment.
We have no affiliation with STMicroelectronics.

## Development

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, run
automatically as a [pre-commit](https://pre-commit.com/) hook.

To set it up, install the dev dependencies and enable the git hook:

    pip install -e ".[dev]"
    pre-commit install

Ruff will then check and format the staged files on every commit. You can also run the
hooks manually against all files:

    pre-commit run --all-files
