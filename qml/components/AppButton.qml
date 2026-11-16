import QtQuick
import QtQuick.Controls

Button {
    id: control

    property bool primary: false
    property bool danger: false
    property bool ghost: false
    property bool compact: false

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitWidth: Math.max(compact ? 34 : 64, label.implicitWidth + (compact ? 18 : 30))
    implicitHeight: compact ? 28 : 36
    opacity: enabled ? 1.0 : 0.45

    font.family: theme.fontFamily
    font.pixelSize: compact ? 11 : 12
    font.weight: Font.Medium
    font.letterSpacing: 0.3

    contentItem: Text {
        id: label
        text: control.text
        font: control.font
        color: control.primary ? theme.onAccent : control.danger ? theme.red : theme.foreground
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 7
        color: {
            if (control.primary)
                return control.down ? theme.accentPressed : control.hovered ? theme.accentHover : theme.accent
            if (control.danger)
                return control.down || control.hovered ? theme.dangerSoft : "transparent"
            if (control.ghost)
                return control.down ? theme.pressed : control.hovered ? theme.hover : "transparent"
            return control.down ? theme.pressed : control.hovered ? theme.hover : theme.surfaceRaised
        }
        border.width: control.primary || control.ghost ? 0 : 1
        border.color: control.danger ? theme.dangerBorder : theme.borderStrong

        Behavior on color {
            ColorAnimation { duration: 100 }
        }
    }
}
