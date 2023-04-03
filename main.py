import os
import subprocess

from admin import run_as_admin
from fpgas import FPGAs
from vivado import Vivado
import PySimpleGUI as sg

INIT = "Initializing..."

ICON_SIZE = 10


def update_toltip(element, tooltip):
    if element.TooltipObject is None or tooltip != element.TooltipObject.text:
        element.set_tooltip(tooltip)


def main():
    vivado = Vivado()
    fpgas = FPGAs()

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
    rows = 0
    window = sg.Window("FPGA device tool", layout)

    # def utils

    def step(title, finish=False):
        if finish:
            step.current = step.total
        elif step.current >= step.total:
            step.total = step.current + 1
        window.write_event_value('one_line_progress_meter',
                                 [["Programming boards", step.current, step.total, title], {'keep_on_top': True}])
        step.current += 1

    def background(function, total):
        step.total = total
        step.current = 0
        window.disable()
        window.perform_long_operation(function, end_key='finished')

    def program():
        preScript = values.get('preScript', '')
        if preScript != '':
            subprocess.call(preScript)
        vivado.program(values['bitstream'])
        postScript = values.get('postScript', '')
        if postScript != '':
            subprocess.call(postScript)

    # init
    window.read(0)
    event, values = "", {}
    while True:

        # update GUI
        fpgas.update()

        # preScript
        hasPreScript = values.get('preScript', '') != ''
        window['preScript'].update(os.path.basename(values['preScript']) if hasPreScript else "Pre script")
        window['preScript'].expand(True)
        update_toltip(
            window['preScript'],
            values['preScript'] if hasPreScript else "Press to run a script before programming a board"
        )
        # bitstream
        hasBitstream = values.get('bitstream', '') != ''
        window['bitstream'].update(os.path.basename(values['bitstream']) if hasBitstream else "Bitstream")
        window['bitstream'].expand(True)
        update_toltip(
            window['bitstream'],
            values['bitstream'] if hasBitstream else "Press to show a bitstream to program"
        )
        # postScript
        hasPostScript = values.get('postScript', '') != ''
        window['postScript'].update(os.path.basename(values['postScript']) if hasPostScript else "Post script")
        window['postScript'].expand(True)
        update_toltip(
            window['postScript'],
            values['postScript'] if hasPostScript else "Press to run a script after programming a board"
        )

        # info
        window['info'].update(f"Boards: {len(fpgas)}")

        # buttons
        window['programAll'].update(disabled=not hasBitstream)
        window['enableAll'].update(disabled=fpgas.allEnabled())
        window['disableAll'].update(disabled=fpgas.allDisabled())

        # foreach fpga
        for i in fpgas:
            # create new row if needed
            if rows < i + 1:
                window.extend_layout(window['boards'], [[sg.Column(
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
                rows += 1

            # show rows
            window[f'row_{i}'].unhide_row()

            # update row
            window[f'icon_{i}'].TKCanvas.create_oval(0, 0, ICON_SIZE, ICON_SIZE,
                                                     fill='green' if fpgas.enabled(i) else 'red')
            window[f'text_{i}'].update(fpgas.name(i))
            update_toltip(window[f'text_{i}'], fpgas.name(i, full=True))
            window[f'toggle_{i}'].update("Disable" if fpgas.enabled(i) else "Enable")
            window[f'program_{i}'].update(disabled=not hasBitstream)

            window[f'row_{i}'].expand(True)  # fixes wrong size after updating

        # hide unused
        for i in range(len(fpgas), rows):
            window[f'row_{i}'].hide_row()

        # wait
        event, values = window.read(timeout=2000 if values.get('autoRefresh', True) else None)

        # act
        if event == sg.WINDOW_CLOSED:
            break  # exit
        elif event in [sg.TIMEOUT_EVENT, 'refresh', 'autoRefresh', 'bitstream', 'preScript', 'postScript']:
            pass  # do nothing

        elif event == 'enableAll':
            def f():
                for i in fpgas:
                    step(f"Enabling board {i + 1}")
                    fpgas.enable(i)

            background(f, len(fpgas))

        elif event == 'disableAll':
            def f():
                for i in fpgas:
                    step(f"Disabling board {i + 1}")
                    fpgas.disable(i)

            background(f, len(fpgas))

        elif event == 'programAll':
            def f():
                with fpgas:
                    for i in fpgas:
                        step(f"Enabling board {i + 1}")
                        fpgas.enable_only(i)
                        if i == 0:
                            step("Initializing Vivado")
                            vivado.prepare()
                        step(f"Programming board {i + 1}")
                        program()

            background(f, 1 + 2 * len(fpgas))

        elif event == 'one_line_progress_meter':
            args, kwargs = values[event]
            sg.one_line_progress_meter(*args, **kwargs)

        elif event == 'finished':
            # sg.one_line_progress_meter_cancel()
            step("Finished", finish=True)
            window.enable()

        elif '_' in event:
            type, i = event.split('_')
            i = int(i)
            if type == 'toggle':
                def f(i):
                    if fpgas.enabled(i):
                        step("Disabling")
                        fpgas.disable(i)
                    else:
                        step("Enabling")
                        fpgas.enable(i)

                background(lambda: f(i), 1)
            elif type == 'enableOnly':
                def f(i):
                    step("Enabling board")
                    fpgas.enable(i)
                    for j in fpgas:
                        if j != i:
                            step(f"Disabling board {j + 1}")
                            fpgas.disable(j)

                background(lambda: f(i), len(fpgas))
            elif type == 'program':
                def f(i):
                    with fpgas:
                        step("Enabling board")
                        fpgas.enable(i)
                        for j in fpgas:
                            if j != i:
                                step(f"Disabling board {j + 1}")
                                fpgas.disable(j)
                        step("Initializing Vivado")
                        vivado.prepare()
                        step("Programming board")
                        program()

                background(lambda: f(i), len(fpgas) + 3)
            else:
                print("Unknown type:", type, i)
        else:
            print("Unknown event:", event)
    window.close()


@run_as_admin
def main_admin():
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        input("exit")


if __name__ == '__main__':
    if 'no_admin' in os.environ:
        main()
    else:
        main_admin()
