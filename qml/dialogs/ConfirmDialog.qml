import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property string titleText: "Are you sure?"
    property string message: ""
    property string confirmLabel: "Delete"
    property bool danger: true

    signal confirmed()

    modal: true
    width: Math.min(440, parent ? parent.width - 64 : 440)
    x: parent ? (parent.width - width) / 2 : 0
    y: parent ? (parent.height - height) / 2 : 0
    padding: 24
    closePolicy: Popup.CloseOnEscape
    focus: true

    Overlay.modal: Rectangle {
        color: theme.scrim
    }

    background: Rectangle {
        color: theme.surfaceRaised
        radius: 12
        border.width: 1
        border.color: theme.borderStrong
    }

    contentItem: ColumnLayout {
        spacing: 16

        Text {
            text: dialog.titleText
            color: theme.foreground
            font.family: theme.fontFamily
            font.pixelSize: 17
            font.weight: Font.DemiBold
        }

        Text {
            Layout.fillWidth: true
            text: dialog.message
            color: theme.foregroundMuted
            font.family: theme.fontFamily
            font.pixelSize: 12
            wrapMode: Text.Wrap
            lineHeight: 1.35
        }

        RowLayout {
            Layout.topMargin: 4
            Layout.fillWidth: true

            Item { Layout.fillWidth: true }

            AppButton {
                text: "Cancel"
                ghost: true
                onClicked: dialog.close()
            }

            AppButton {
                text: dialog.confirmLabel
                danger: dialog.danger
                onClicked: {
                    dialog.confirmed()
                    dialog.close()
                }
            }
        }
    }
}
