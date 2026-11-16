import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    property string label: ""
    property string value: ""

    spacing: 5

    Text {
        text: root.label.toUpperCase()
        color: theme.foregroundDim
        font.family: theme.fontFamily
        font.pixelSize: 9
        font.letterSpacing: 1.3
    }

    Text {
        text: root.value.length ? root.value : "—"
        color: root.value.length ? theme.foreground : theme.foregroundDim
        font.family: theme.fontFamily
        font.pixelSize: 13
        wrapMode: Text.Wrap
        Layout.fillWidth: true
    }
}
