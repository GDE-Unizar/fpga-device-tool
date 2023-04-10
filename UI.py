import os
import subprocess

import PySimpleGUI as sg

TIMEOUT = 500

INIT = "Initializing..."
ICON_SIZE = 10


class UI:
    def __init__(self):
        """
        Initializes the UI
        """

        self.running = False
        self.current = 0
        self.total = 0

        layout = [
            # top row
            [
                # info
                sg.Text(INIT, key='info', expand_x=True),

                # middle buttons
                sg.Column([[
                    sg.FileBrowse(INIT, key='preScript', tooltip=INIT, enable_events=True, target='preScript'),
                    sg.FileBrowse(INIT, file_types=(("Bitstreams", '*.bit'), ("ALL Files", '.*')), key='bitstream', tooltip=INIT, enable_events=True, target='bitstream'),
                    sg.FileBrowse(INIT, key='postScript', tooltip=INIT, enable_events=True, target='postScript'),
                ]], expand_x=True, element_justification='Center'),

                # right buttons
                sg.Column([[
                    sg.Button("Enable all", key='enableAll'),
                    sg.Button("Disable all", key='disableAll'),
                    sg.Button("Program all", key='programAll'),
                ]], expand_x=True, element_justification='Right'),
            ],
            [sg.HorizontalSeparator()],

            # containers
            [sg.Column([], key='boards', expand_x=True)],

            # bottom buttons
            [sg.Column([[
                sg.Checkbox("Auto-refresh", True, key='autoRefresh', enable_events=True),
                sg.Button("Refresh", key='refresh')
            ]], expand_x=True, element_justification='Right')],
        ]
        self.rows = 0
        self.window = sg.Window("FPGA device tool", layout, icon=os.path.join(os.path.dirname(__file__), 'logo.ico'))

        _, self.values = self.window.read(0)

    def update(self, fpgas):
        """
        Updates the UI with the current state and the given fpgas
        """

        # preScript
        hasPreScript = self.values.get('preScript', '') != ''
        self.window['preScript'].update(os.path.basename(self.values['preScript']) if hasPreScript else "Pre script")
        self.window['preScript'].expand(True)
        update_toltip(
            self.window['preScript'],
            self.values['preScript'] if hasPreScript else "Press to run a script before programming a board"
        )
        # bitstream
        hasBitstream = self.values.get('bitstream', '') != ''
        self.window['bitstream'].update(os.path.basename(self.values['bitstream']) if hasBitstream else "Bitstream")
        self.window['bitstream'].expand(True)
        update_toltip(
            self.window['bitstream'],
            self.values['bitstream'] if hasBitstream else "Press to show a bitstream to program"
        )
        # postScript
        hasPostScript = self.values.get('postScript', '') != ''
        self.window['postScript'].update(os.path.basename(self.values['postScript']) if hasPostScript else "Post script")
        self.window['postScript'].expand(True)
        update_toltip(
            self.window['postScript'],
            self.values['postScript'] if hasPostScript else "Press to run a script after programming a board"
        )

        # info
        self.window['info'].update(f"Boards: {len(fpgas)}")

        # buttons
        self.window['programAll'].update(disabled=not hasBitstream)
        self.window['enableAll'].update(disabled=fpgas.allEnabled())
        self.window['disableAll'].update(disabled=fpgas.allDisabled())

        # foreach fpga
        for i in fpgas:
            # create new row if needed
            if self.rows < i + 1:
                self.window.extend_layout(self.window['boards'], [[sg.Column(
                    [[
                        sg.Canvas(size=(ICON_SIZE + 1, ICON_SIZE + 1), key=f'icon_{i}'),
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
            self.window[f'icon_{i}'].TKCanvas.create_oval(0, 0, ICON_SIZE, ICON_SIZE,
                                                          fill='green' if fpgas.enabled(i) else 'red')
            self.window[f'text_{i}'].update(fpgas.name(i))
            update_toltip(self.window[f'text_{i}'], fpgas.name(i, full=True))
            self.window[f'toggle_{i}'].update("Disable" if fpgas.enabled(i) else "Enable")
            self.window[f'program_{i}'].update(disabled=not hasBitstream)

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
            self.running = sg.one_line_progress_meter(*args, **kwargs)
            if not self.running:
                self.window.force_focus()

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

    def background(self, function, total):
        self.running = True
        self.total = total
        self.current = 0
        self.window.disable()
        self.window.perform_long_operation(lambda: self._background(function), end_key='finished')

    def _background(self, function):
        try:
            function()
        except CancelException:
            pass

class CancelException(Exception):
    pass

def update_toltip(element, tooltip):
    if element.TooltipObject is None or tooltip != element.TooltipObject.text:
        element.set_tooltip(tooltip)
