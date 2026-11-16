import QtQuick
import QtQuick.Controls

Item {
    id: root

    property alias text: field.text
    property string placeholderText: ""
    property var suggestions: []

    signal picked(string value)
    signal accepted()

    implicitWidth: 240
    implicitHeight: 40

    readonly property var filtered: {
        const query = field.text.trim().toLowerCase()
        if (!query)
            return []
        const result = []
        for (let i = 0; i < root.suggestions.length; ++i) {
            const candidate = String(root.suggestions[i])
            const lower = candidate.toLowerCase()
            if (lower !== query && lower.indexOf(query) !== -1)
                result.push(candidate)
            if (result.length >= 6)
                break
        }
        return result
    }

    function choose(value) {
        field.text = value
        popup.close()
        field.forceActiveFocus()
        root.picked(value)
    }

    function move(step) {
        if (!popup.visible || root.filtered.length === 0)
            return
        popup.highlighted = (popup.highlighted + step + root.filtered.length) % root.filtered.length
    }

    function chooseCurrent() {
        if (popup.visible && popup.highlighted >= 0 && popup.highlighted < root.filtered.length)
            choose(root.filtered[popup.highlighted])
        else
            root.accepted()
    }

    function focusInput() {
        field.forceActiveFocus()
    }

    AppTextField {
        id: field
        width: root.width
        placeholderText: root.placeholderText
        onTextEdited: popup.highlighted = 0
        onActiveFocusChanged: if (!activeFocus) popup.close()
        onAccepted: root.chooseCurrent()

        Keys.onDownPressed: {
            root.move(1)
            event.accepted = true
        }
        Keys.onUpPressed: {
            root.move(-1)
            event.accepted = true
        }
    }

    Popup {
        id: popup

        property int highlighted: 0

        x: 0
        y: field.height + 4
        width: root.width
        visible: field.activeFocus && root.filtered.length > 0
        padding: 4
        focus: false
        closePolicy: Popup.NoAutoClose

        background: Rectangle {
            color: theme.surfaceRaised
            radius: 8
            border.width: 1
            border.color: theme.borderStrong
        }

        contentItem: ListView {
            implicitHeight: Math.min(root.filtered.length, 6) * 32
            model: root.filtered
            clip: true

            delegate: Rectangle {
                required property int index
                required property var modelData

                width: ListView.view.width
                height: 32
                radius: 5
                color: index === popup.highlighted ? theme.selection
                                                     : hover.containsMouse ? theme.hover : "transparent"

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 12
                }

                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPressed: root.choose(modelData)
                }
            }
        }
    }
}
