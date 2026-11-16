import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var concert: null
    property var otherBands: []
    property string errorText: ""

    signal saved(int concertId)

    modal: true
    width: Math.min(680, parent ? parent.width - 56 : 680)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? Math.max(20, (parent.height - height) / 2) : 0
    padding: 24
    closePolicy: Popup.CloseOnEscape

    Overlay.modal: Rectangle {
        color: theme.scrim
    }

    background: Rectangle {
        color: theme.surfaceRaised
        radius: 12
        border.width: 1
        border.color: theme.borderStrong
    }

    function openFor(show) {
        concert = show
        errorText = ""
        otherBands = []
        if (show) {
            headlinerField.text = show.band
            eventField.text = show.event
            dateField.text = show.date
            endDateField.text = show.endDate
            venueField.text = show.venue
            cityField.text = show.city
            otherBands = show.otherBands.slice()
            notesArea.text = show.notes
        } else {
            headlinerField.text = ""
            eventField.text = ""
            dateField.text = Qt.formatDate(new Date(), "yyyy-MM-dd")
            endDateField.text = ""
            venueField.text = ""
            cityField.text = ""
            notesArea.text = ""
        }
        open()
    }

    function openDatePicker() {
        dateField.openPicker()
    }

    function addSupporting(value) {
        const name = String(value).trim()
        if (!name)
            return
        const lower = name.toLowerCase()
        if (lower === headlinerField.text.trim().toLowerCase())
            return
        for (let i = 0; i < otherBands.length; ++i) {
            if (otherBands[i].toLowerCase() === lower) {
                otherBandField.text = ""
                return
            }
        }
        otherBands = otherBands.concat([name])
        otherBandField.text = ""
    }

    function removeSupporting(index) {
        const copy = otherBands.slice()
        copy.splice(index, 1)
        otherBands = copy
    }

    function save() {
        errorText = ""
        const result = backend.saveConcert({
            id: concert ? concert.id : 0,
            band: headlinerField.text,
            event: eventField.text,
            date: dateField.text,
            endDate: endDateField.text,
            venue: venueField.text,
            city: cityField.text,
            otherBands: otherBands,
            notes: notesArea.text
        })
        if (!result.ok) {
            errorText = result.error
            return
        }
        close()
        saved(result.id)
    }

    onOpened: headlinerField.focusInput()

    contentItem: ColumnLayout {
        spacing: 15

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 3

                Text {
                    text: dialog.concert ? "EDIT SHOW" : "NEW SHOW"
                    color: theme.accent
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.6
                }

                Text {
                    text: dialog.concert ? "Update this concert" : "Log a concert"
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                }
            }

            Item { Layout.fillWidth: true }

            AppButton {
                compact: true
                ghost: true
                text: "×"
                implicitWidth: 34
                onClicked: dialog.close()
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            Text {
                text: "HEADLINER"
                color: theme.foregroundDim
                font.family: theme.fontFamily
                font.pixelSize: 9
                font.letterSpacing: 1.3
            }

            SuggestField {
                id: headlinerField
                Layout.fillWidth: true
                placeholderText: "Band name — type a new one to add it"
                suggestions: backend.bands
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.preferredWidth: 185
                spacing: 5

                Text {
                    text: "DATE"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                DateField {
                    id: dateField
                    Layout.fillWidth: true
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 185
                spacing: 5

                Text {
                    text: "END DATE (OPTIONAL)"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                DateField {
                    id: endDateField
                    Layout.fillWidth: true
                    clearable: true
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5

                Text {
                    text: "EVENT / FESTIVAL"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                SuggestField {
                    id: eventField
                    Layout.fillWidth: true
                    placeholderText: "Copenhell, festival, tour…"
                    suggestions: backend.events
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5

                Text {
                    text: "VENUE"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                SuggestField {
                    id: venueField
                    Layout.fillWidth: true
                    placeholderText: "Venue"
                    suggestions: backend.venues
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5

                Text {
                    text: "LOCATION"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                SuggestField {
                    id: cityField
                    Layout.fillWidth: true
                    placeholderText: "City"
                    suggestions: backend.cities
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 7

            RowLayout {
                spacing: 8

                Text {
                    text: "OTHER BANDS"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.3
                }

                Text {
                    text: "support acts, optional"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    opacity: 0.7
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: dialog.otherBands

                    delegate: Chip {
                        required property int index
                        required property var modelData

                        label: modelData
                        removable: true
                        onRemoved: dialog.removeSupporting(index)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                SuggestField {
                    id: otherBandField
                    Layout.fillWidth: true
                    placeholderText: "Add a support act"
                    suggestions: backend.bands
                    onAccepted: dialog.addSupporting(text)
                    onPicked: (value) => dialog.addSupporting(value)
                }

                AppButton {
                    text: "Add"
                    ghost: true
                    onClicked: dialog.addSupporting(otherBandField.text)
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            Text {
                text: "NOTES"
                color: theme.foregroundDim
                font.family: theme.fontFamily
                font.pixelSize: 9
                font.letterSpacing: 1.3
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 82
                color: theme.inputBackground
                radius: 7
                border.width: 1
                border.color: notesArea.activeFocus ? theme.accent : theme.border

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 2
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    TextArea {
                        id: notesArea
                        placeholderText: "Setlist memories, who you went with, anything worth remembering…"
                        placeholderTextColor: theme.foregroundDim
                        color: theme.foreground
                        selectionColor: theme.accent
                        selectedTextColor: theme.onAccent
                        font.family: theme.fontFamily
                        font.pixelSize: 12
                        wrapMode: TextArea.Wrap
                        background: null
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: dialog.errorText.length > 0
            text: dialog.errorText
            color: theme.red
            font.family: theme.fontFamily
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }

        RowLayout {
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            AppButton {
                text: "Cancel"
                ghost: true
                onClicked: dialog.close()
            }

            AppButton {
                text: dialog.concert ? "Save changes" : "Add show"
                primary: true
                onClicked: dialog.save()
            }
        }
    }
}
