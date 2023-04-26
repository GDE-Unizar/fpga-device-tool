import os

import PySimpleGUI as sg

TIMEOUT = 500

INIT = "Initializing..."
ICON_SIZE = 10

sg.theme('SystemDefaultForReal')


class UI:
    def __init__(self):
        """
        Initializes the UI
        """

        self.running = False
        self.current = 0
        self.total = 0

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

        program_layout = sg.Frame(title="Programming", vertical_alignment='top', layout=[
            [sg.Checkbox("Pause before running pre-script", key="prePrePause")],
            [
                sg.FileBrowse(INIT, key='preScriptSet', tooltip=INIT, target='preScript'),
                sg.Input(key='preScript', enable_events=True, visible=False),
                sg.Button("X", key='clear_preScript', visible=False),
            ],
            [sg.Checkbox("Pause before programming", key="prePause")],
            [
                sg.FileBrowse(INIT, file_types=(("Bitstreams", '*.bit'), ("ALL Files", '.*')), key='bitstreamSet', tooltip=INIT, target='bitstream'),
                sg.Input(key='bitstream', enable_events=True, visible=False),
                sg.Button("X", key='clear_bitstream', visible=False),
            ],
            [sg.Checkbox("Pause after programming", key="postPause")],
            [
                sg.FileBrowse(INIT, key='postScriptSet', tooltip=INIT, target='postScript'),
                sg.Input(key='postScript', enable_events=True, visible=False),
                sg.Button("X", key='clear_postScript', visible=False),
            ],
            [sg.Checkbox("Pause after running post-script", key="prePrePause")],
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

        # preScript
        hasPreScript = self.values.get('preScript', '') != ''
        self.window['preScriptSet'].update(os.path.basename(self.values['preScript']) if hasPreScript else "No pre script")
        self.window['preScriptSet'].expand(True)
        update_toltip(
            self.window['preScriptSet'],
            self.values['preScriptSet'] if hasPreScript else "Press to run a script before programming a board"
        )
        self.window['clear_preScript'].update(visible=hasPreScript)

        # bitstream
        hasBitstream = self.values.get('bitstream', '') != ''
        self.window['bitstreamSet'].update(os.path.basename(self.values['bitstream']) if hasBitstream else "No bitstream")
        self.window['bitstreamSet'].expand(True)
        update_toltip(
            self.window['bitstreamSet'],
            self.values['bitstreamSet'] if hasBitstream else "Press to show a bitstream to program"
        )
        self.window['clear_bitstream'].update(visible=hasBitstream)

        # postScript
        hasPostScript = self.values.get('postScript', '') != ''
        self.window['postScriptSet'].update(os.path.basename(self.values['postScript']) if hasPostScript else "No post script")
        self.window['postScriptSet'].expand(True)
        update_toltip(
            self.window['postScriptSet'],
            self.values['postScriptSet'] if hasPostScript else "Press to run a script after programming a board"
        )
        self.window['clear_postScript'].update(visible=hasPostScript)

        canProgram = hasPreScript or hasBitstream or hasPostScript

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
        self.window.write_event_value('popup', [
            [message, "", "Press to continue"], {'title': "Wait", 'custom_text': "continue", 'keep_on_top': True}
        ])

    def clear(self, key):
        # should be native, but it isn't
        self.window[key]('')
        self.values[key] = ''


class CancelException(Exception):
    pass


def update_toltip(element, tooltip):
    if element.TooltipObject is None or tooltip != element.TooltipObject.text:
        element.set_tooltip(tooltip)
