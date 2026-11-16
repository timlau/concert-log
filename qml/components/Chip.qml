import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string label: ""
    property bool removable: false
    signal removed()

    implicitWidth: chipRow.implicitWidth + 22
    implicitHeight: 26
    radius: 13
    color: theme.accentSoft
    border.width: 1
    border.color: theme.accentBorder

    Row {
        id: chipRow
        anchors.centerIn: parent
        spacing: 6

        Text {
            text: root.label
            color: theme.foreground
            font.family: theme.fontFamily
            font.pixelSize: 11
            anchors.verticalCenter: parent.verticalCenter
        }

        Item {
            visible: root.removable
            width: visible ? 12 : 0
            height: 12
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: "×"
                color: theme.foregroundMuted
                font.family: theme.fontFamily
                font.pixelSize: 13
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.removed()
            }
        }
    }
}
