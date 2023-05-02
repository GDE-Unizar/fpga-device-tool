import os
from threading import Event

import PySimpleGUI as sg

TIMEOUT = 1000

INIT = "Initializing..."
ICON_SIZE = 10


class UI:
    def __init__(self, is_vivado_available):
        """
        Initializes the UI
        """
        self.waiting = Event()
        self.running = False
        self.current = 0
        self.total = 0
        self.steps_values = []

        sg.theme('SystemDefaultForReal')

        boards_layout = sg.Frame(title=INIT, key="info", expand_y=True, layout=[
            [
                # refresh
                sg.Column(expand_x=True, element_justification='Left', layout=[[
                    sg.Checkbox("Auto-refresh", True, key='autoRefresh', enable_events=True),
                    sg.Button("Refresh", key='refresh')
                ]]),
                # buttons
                sg.Column(expand_x=True, element_justification='Right', layout=[[
                    sg.Button("Enable all", key='enableAll'),
                    sg.Button("Disable all", key='disableAll'),
                    sg.Button("Program all", key='programAll'),
                ]]),
            ],

            # separation
            [sg.HorizontalSeparator()],

            # container
            [sg.Column([], key='boards', expand_x=True)],
        ])

        program_layout = sg.Frame(title=INIT, key="stepsFrame", vertical_alignment='top', expand_y=True, layout=[
            [
                sg.Listbox(expand_x=True, expand_y=True, key='steps', values=[], enable_events=True),

                sg.Column(layout=[
                    [sg.Button("/\\", key='stepsUp')],
                    [sg.Button("X", key='stepsRemove')],
                    [sg.Button("\\/", key='stepsDown')],
                ]),
            ],
            [
                sg.Button("Add pause", key='stepsPause'),
                sg.FileBrowse("Add script", target='stepsScript'),
                sg.Input(key='stepsScript', enable_events=True, visible=False),
                sg.FileBrowse("Add bitstream", target='stepsBitstream', visible=is_vivado_available),
                sg.Input(key='stepsBitstream', enable_events=True, visible=False),
            ],
        ])
        self.rows = 0
        self.window = sg.Window(
            "FPGA device tool",
            [[boards_layout, program_layout]],
            icon=os.path.join(os.path.dirname(__file__), 'logo.ico'),
        )

        _, self.values = self.window.read(0)

    def update(self, fpgas):
        """
        Updates the UI with the current state and the given fpgas
        """

        # steps
        selection = self.get_steps_selection()
        self.window['stepsUp'](disabled=selection is None or selection <= 0)
        self.window['stepsRemove'](disabled=selection is None)
        self.window['stepsDown'](disabled=selection is None or selection >= len(self.steps_values) - 1)
        canProgram = len(self.steps_values) > 0
        self.window['stepsFrame'](f"Program steps: {len(self.steps_values)}")

        # info
        self.window['info'].update(f"Boards: {len(fpgas)}")

        # buttons
        self.window['programAll'].update(disabled=not canProgram)
        self.window['enableAll'].update(disabled=fpgas.allEnabled())
        self.window['disableAll'].update(disabled=fpgas.allDisabled())

        # foreach fpga
        for i in fpgas:
            # create new row if needed
            if self.rows < i + 1:
                self.window.extend_layout(self.window['boards'], [[sg.Column(
                    [[
                        sg.Canvas(size=(ICON_SIZE, ICON_SIZE), key=f'icon_{i}'),
                        sg.Text(key=f'text_{i}', expand_x=True),
                        sg.Button("Enable only", key=f'enableOnly_{i}'),
                        sg.Button("Toggle", key=f'toggle_{i}'),
                        sg.Button("Program", key=f'program_{i}'),
                    ]],
                    key=f'row_{i}',
                    expand_x=True,
                )], ])
                self.rows += 1

            # show rows
            self.window[f'row_{i}'].unhide_row()

            # update row
            self.window[f'icon_{i}'].tk_canvas.create_oval(2, 2, ICON_SIZE, ICON_SIZE, fill='green' if fpgas.enabled(i) else 'red')
            self.window[f'text_{i}'].update(fpgas.name(i))
            update_toltip(self.window[f'text_{i}'], fpgas.id(i))
            self.window[f'toggle_{i}'].update("Disable" if fpgas.enabled(i) else "Enable")
            self.window[f'program_{i}'].update(disabled=not canProgram)

            self.window[f'row_{i}'].expand(True)  # fixes wrong size after updating

        # hide unused
        for i in range(len(fpgas), self.rows):
            self.window[f'row_{i}'].hide_row()

    def is_shown(self):
        """
        returns true iff the window is being shown
        """
        return not self.window.was_closed()

    def get_value(self, name, default=''):
        """
        returns a value from the window
        """
        return self.values.get(name, default)

    def get_steps_selection(self):
        return (self.window['steps'].get_indexes() + (None,))[0]

    def tick(self):
        """
        Performs a windows tick.
        Returns the fired event
        """
        event, self.values = self.window.read(timeout=TIMEOUT if self.values.get('autoRefresh', True) else None)

        # act
        if event == sg.WINDOW_CLOSED:
            self.window.close()
            pass  # exit

        elif event in [sg.TIMEOUT_EVENT]:
            pass  # do nothing

        elif event == 'one_line_progress_meter':
            # called from background process, update progress
            args, kwargs = self.values[event]
            self.running = self.running and sg.one_line_progress_meter(*args, **kwargs)
            if not self.running:
                self.window.force_focus()

        elif event == 'popup':
            # called from background process, show popup
            args, kwargs = self.values[event]
            sg.popup(*args, **kwargs)
            self.waiting.set()

        elif event == 'finished':
            # finished background process, hide process and reenable
            self.running = False
            sg.one_line_progress_meter_cancel()
            self.window.enable()
            self.window.force_focus()

        else:
            # find event
            splits = event.split("_")
            if hasattr(self, splits[0]):
                getattr(self, splits[0])(*splits[1:])
            else:
                print("No function exists for event:", event)

    def background(self, function, total):
        """
        Starts a background process
        """
        self.running = True
        self.total = total
        self.current = 0
        self.window.disable()

        def _background(function):
            try:
                function()
            except CancelException:
                pass

        self.window.perform_long_operation(lambda: _background(function), end_key='finished')

    def step(self, title):
        """
        Updates the progress of a background progress
        """
        if not self.running: raise CancelException()

        # avoid closing if total was less than real
        if self.current >= self.total:
            print("no more steps, increasing by 1")
            self.total = self.current + 1

        # send event to main loop to process
        self.window.write_event_value('one_line_progress_meter', [
            ["Programming boards", self.current, self.total, title], {'keep_on_top': True}
        ])

        # prepare next
        self.current += 1
        if not self.running:
            raise CancelException()

    def wait(self, message):
        """
        Asks the user to continue
        """
        self.waiting.clear()
        self.window.write_event_value('popup', [
            [message, "", "Press to continue"], {'title': "Wait", 'custom_text': "continue", 'keep_on_top': True}
        ])
        self.waiting.wait()

    def clear(self, key):
        # should be native, but it isn't
        self.window[key]('')
        self.values[key] = ''

class CancelException(Exception):
    pass


def update_toltip(element, tooltip):
    if element.TooltipObject is None or tooltip != element.TooltipObject.text:
        element.set_tooltip(tooltip)
