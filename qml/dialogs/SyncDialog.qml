import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property string statusText: ""
    property bool statusError: false

    modal: true
    width: Math.min(560, parent ? parent.width - 56 : 560)
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

    function runExport(fileUrl) {
        const result = backend.exportData(String(fileUrl))
        if (!result.ok) {
            setStatus(result.error, true)
            return
        }
        const name = result.path.split("/").pop()
        setStatus("Saved " + result.shows + " shows to " + name, false)
    }

    function runMarkdownExport() {
        const result = backend.exportMarkdown()
        if (!result.ok) {
            setStatus(result.error, true)
            return
        }
        setStatus("Saved " + result.shows + " notes to " + result.directory, false)
    }

    function runImport(fileUrl) {
        const result = backend.importData(String(fileUrl))
        if (!result.ok) {
            setStatus(result.error, true)
            return
        }
        const parts = []
        if (result.added > 0)
            parts.push(result.added + " new")
        if (result.updated > 0)
            parts.push(result.updated + " updated")
        if (parts.length === 0)
            parts.push("already up to date")
        let message = "Import complete: " + parts.join(", ")
        if (result.photos > 0)
            message += " · " + result.photos
                       + (result.photos === 1 ? " photo" : " photos")
        setStatus(message, false)
    }

    function setStatus(message, isError) {
        statusText = message
        statusError = isError
        if (typeof window.showToast === "function")
            window.showToast(message)
    }

    contentItem: ColumnLayout {
        spacing: 13

        Text {
            text: "DATA & SYNC"
            color: theme.accent
            font.family: theme.fontFamily
            font.pixelSize: 9
            font.letterSpacing: 1.6
        }

        Text {
            Layout.fillWidth: true
            text: "Move your log between computers"
            color: theme.foreground
            font.family: theme.fontFamily
            font.pixelSize: 20
            font.weight: Font.DemiBold
        }

        Text {
            Layout.fillWidth: true
            text: "An export is one .zip containing every show, artist, and setlist photo. "
                  + "Import merges that file into this computer's log: new shows are added "
                  + "and newer edits replace older ones. Shows deleted here stay deleted "
                  + "here — imports never remove local data. You can also export one "
                  + "Markdown note per show to your notes folder."
            color: theme.foregroundMuted
            font.family: theme.fontFamily
            font.pixelSize: 11
            wrapMode: Text.Wrap
            lineHeight: 1.4
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: theme.inputBackground
            radius: 9
            border.width: 1
            border.color: theme.border

            Column {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 130
                spacing: 4

                Text {
                    text: "Export a copy"
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                Text {
                    width: parent.width
                    text: "Save a backup you can copy to the other computer."
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }

            AppButton {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "Export…"
                ghost: true
                onClicked: exportFileDialog.open()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: theme.inputBackground
            radius: 9
            border.width: 1
            border.color: theme.border

            Column {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 130
                spacing: 4

                Text {
                    text: "Export concert notes"
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                Text {
                    width: parent.width
                    text: "Write one .md file per show to the folder set in config.toml. Existing files are replaced."
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }

            AppButton {
                objectName: "exportMarkdownButton"
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "Export notes"
                ghost: true
                onClicked: dialog.runMarkdownExport()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: theme.inputBackground
            radius: 9
            border.width: 1
            border.color: theme.border

            Column {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 130
                spacing: 4

                Text {
                    text: "Import an export"
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                Text {
                    width: parent.width
                    text: "Merge a .zip from the other computer into this log."
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }

            AppButton {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "Import…"
                primary: true
                onClicked: importFileDialog.open()
            }
        }

        Text {
            Layout.fillWidth: true
            visible: dialog.statusText.length > 0
            text: dialog.statusText
            color: dialog.statusError ? theme.red : theme.green
            font.family: theme.fontFamily
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 2

            Text {
                text: "Tip: keep the .zip in a shared folder to move both ways."
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

    FileDialog {
        id: exportFileDialog
        objectName: "exportFileDialog"

        title: "Export Concert Log"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["Concert Log archive (*.zip)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        currentFile: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
                     + "/concert-log-" + Qt.formatDate(new Date(), "yyyy-MM-dd") + ".zip"
        onAccepted: dialog.runExport(selectedFile)
    }

    FileDialog {
        id: importFileDialog
        objectName: "importFileDialog"

        title: "Import Concert Log"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Concert Log archive (*.zip)"]
        currentFolder: StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        onAccepted: dialog.runImport(selectedFile)
    }
}
