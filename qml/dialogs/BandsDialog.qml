import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property string errorText: ""
    property var pendingBand: null

    modal: true
    width: Math.min(580, parent ? parent.width - 56 : 580)
    height: Math.min(620, parent ? parent.height - 56 : 620)
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

    function addArtist(name) {
        errorText = ""
        const result = backend.addBand(name)
        if (!result.ok) {
            errorText = result.error
            return
        }
        addField.text = ""
        addField.focusInput()
    }

    function askDelete(band) {
        pendingBand = band
        deleteConfirm.message = "Remove " + band.name + " from the artist list?"
                                          + (band.count > 0
                                             ? " They appear in " + band.count
                                               + (band.count === 1 ? " show" : " shows") + "."
                                             : "")
        deleteConfirm.open()
    }

    onOpened: {
        errorText = ""
        addField.text = ""
        addField.focusInput()
    }

    contentItem: ColumnLayout {
        spacing: 14

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                spacing: 3

                Text {
                    text: "ARTISTS"
                    color: theme.accent
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.6
                }

                Text {
                    text: backend.bandRows.length + (backend.bandRows.length === 1 ? " artist" : " artists")
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

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            SuggestField {
                id: addField
                Layout.fillWidth: true
                placeholderText: "Add an artist by name"
                suggestions: []
                onAccepted: dialog.addArtist(text)
            }

            AppButton {
                text: "Add"
                ghost: true
                onClicked: dialog.addArtist(addField.text)
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

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: artistList

                anchors.fill: parent
                clip: true
                model: backend.bandRows
                spacing: 2
                boundsBehavior: Flickable.StopAtBounds

                delegate: Rectangle {
                    id: artistRow

                    required property var modelData

                    width: ListView.view.width
                    height: 46
                    radius: 7
                    color: rowMouse.containsMouse ? theme.hover : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        AppTextField {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 34
                            text: artistRow.modelData.name
                            onEditingFinished: {
                                const value = text.trim()
                                if (value === artistRow.modelData.name)
                                    return
                                const result = backend.renameBand(artistRow.modelData.id, value)
                                if (!result.ok) {
                                    dialog.errorText = result.error
                                    text = artistRow.modelData.name
                                } else {
                                    dialog.errorText = ""
                                }
                            }
                        }

                        Text {
                            Layout.preferredWidth: 62
                            horizontalAlignment: Text.AlignRight
                            text: artistRow.modelData.count
                                  + (artistRow.modelData.count === 1 ? " show" : " shows")
                            color: theme.foregroundDim
                            font.family: theme.fontFamily
                            font.pixelSize: 10
                        }

                        AppButton {
                            compact: true
                            ghost: true
                            danger: true
                            text: "Delete"
                            onClicked: dialog.askDelete(artistRow.modelData)
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        propagateComposedEvents: true
                        acceptedButtons: Qt.NoButton
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    id: scrollBar

                    policy: ScrollBar.AsNeeded
                    width: 9

                    contentItem: Rectangle {
                        implicitWidth: 4
                        radius: 2
                        color: theme.foregroundDim
                        opacity: scrollBar.pressed ? 0.9 : scrollBar.active ? 0.55 : 0.25
                    }

                    background: Rectangle {
                        color: "transparent"
                    }
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                visible: backend.bandRows.length === 0
                spacing: 8

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "♪"
                    color: theme.accent
                    opacity: 0.45
                    font.family: theme.fontFamily
                    font.pixelSize: 36
                }

                Text {
                    text: "No artists yet. Add one above."
                    color: theme.foregroundMuted
                    font.family: theme.fontFamily
                    font.pixelSize: 11
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "Names save when you leave the field."
                color: theme.foregroundDim
                font.family: theme.fontFamily
                font.pixelSize: 10
            }

            Item { Layout.fillWidth: true }

            AppButton {
                text: "Close"
                ghost: true
                onClicked: dialog.close()
            }
        }
    }

    ConfirmDialog {
        id: deleteConfirm

        parent: Overlay.overlay
        titleText: "Remove artist?"
        confirmLabel: "Remove"
        onConfirmed: {
            if (!dialog.pendingBand)
                return
            const result = backend.deleteBand(dialog.pendingBand.id)
            if (!result.ok)
                dialog.errorText = result.error
            else
                dialog.errorText = ""
            dialog.pendingBand = null
        }
    }
}
