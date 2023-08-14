import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *


class SegmentEditorMaskVolumeEffect(AbstractScriptedSegmentEditorEffect):
    """This effect fills a selected volume node inside and/or outside a segment with a chosen value.
    """

    def __init__(self, scriptedEffect):
        scriptedEffect.name = 'Mask volume'
        scriptedEffect.perSegment = True  # this effect operates on a single selected segment
        AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

        # Effect-specific members
        self.buttonToOperationNameMap = {}

    def clone(self):
        # It should not be necessary to modify this method
        import qSlicerSegmentationsEditorEffectsPythonQt as effects
        clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
        clonedEffect.setPythonSource(__file__.replace('\\', '/'))
        return clonedEffect

    def icon(self):
        # It should not be necessary to modify this method
        iconPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons/MaskVolume.png')
        if os.path.exists(iconPath):
            return qt.QIcon(iconPath)
        return qt.QIcon()

    def helpText(self):
        return """<html>使用当前选定分割作为蒙版来消除数据中的区域。
<br> 默认情况下，蒙版会应用于源数据。<p>
填充内部和外部操作创建一个二进制的标签图作为输出，内部和外部填充值可以修改。
</html>"""

    def setupOptionsFrame(self):
        self.operationRadioButtons = []
        self.updatingGUIFromMRML = False
        self.visibleIcon = qt.QIcon(":/Icons/Small/SlicerVisible.png")
        self.invisibleIcon = qt.QIcon(":/Icons/Small/SlicerInvisible.png")

        # Fill operation buttons
        self.fillInsideButton = qt.QRadioButton("填充内部")
        self.operationRadioButtons.append(self.fillInsideButton)
        self.buttonToOperationNameMap[self.fillInsideButton] = 'FILL_INSIDE'

        self.fillOutsideButton = qt.QRadioButton("填充外部")
        self.operationRadioButtons.append(self.fillOutsideButton)
        self.buttonToOperationNameMap[self.fillOutsideButton] = 'FILL_OUTSIDE'

        self.binaryMaskFillButton = qt.QRadioButton("同时填充")
        self.binaryMaskFillButton.setToolTip("创建具有指定内部和外部填充值的标签图数据。")
        self.operationRadioButtons.append(self.binaryMaskFillButton)
        self.buttonToOperationNameMap[self.binaryMaskFillButton] = 'FILL_INSIDE_AND_OUTSIDE'

        # Operation buttons layout
        operationLayout = qt.QGridLayout()
        operationLayout.addWidget(self.fillInsideButton, 0, 0)
        operationLayout.addWidget(self.fillOutsideButton, 1, 0)
        operationLayout.addWidget(self.binaryMaskFillButton, 0, 1)
        self.scriptedEffect.addLabeledOptionsWidget("操作：", operationLayout)

        # fill value
        self.fillValueEdit = ctk.ctkDoubleSpinBox()
        self.fillValueEdit.setToolTip("选择将用于填充蒙版区域的体素强度。")
        self.fillValueLabel = qt.QLabel("填充值：")

        # Binary mask fill outside value
        self.binaryMaskFillOutsideEdit = ctk.ctkDoubleSpinBox()
        self.binaryMaskFillOutsideEdit.setToolTip("选择将用于填充蒙版外部的体素强度。")
        self.fillOutsideLabel = qt.QLabel("外部填充值： ")

        # Binary mask fill outside value
        self.binaryMaskFillInsideEdit = ctk.ctkDoubleSpinBox()
        self.binaryMaskFillInsideEdit.setToolTip("选择将用于填充蒙版内部的体素强度。")
        self.fillInsideLabel = qt.QLabel("内部填充值： ")

        for fillValueEdit in [self.fillValueEdit, self.binaryMaskFillOutsideEdit, self.binaryMaskFillInsideEdit]:
            fillValueEdit.decimalsOption = ctk.ctkDoubleSpinBox.DecimalsByValue + ctk.ctkDoubleSpinBox.DecimalsByKey + ctk.ctkDoubleSpinBox.InsertDecimals
            fillValueEdit.minimum = vtk.vtkDoubleArray().GetDataTypeMin(vtk.VTK_DOUBLE)
            fillValueEdit.maximum = vtk.vtkDoubleArray().GetDataTypeMax(vtk.VTK_DOUBLE)
            fillValueEdit.connect("valueChanged(double)", self.fillValueChanged)

        # Fill value layouts
        fillValueLayout = qt.QFormLayout()
        fillValueLayout.addRow(self.fillValueLabel, self.fillValueEdit)

        fillOutsideLayout = qt.QFormLayout()
        fillOutsideLayout.addRow(self.fillOutsideLabel, self.binaryMaskFillOutsideEdit)

        fillInsideLayout = qt.QFormLayout()
        fillInsideLayout.addRow(self.fillInsideLabel, self.binaryMaskFillInsideEdit)

        binaryMaskFillLayout = qt.QHBoxLayout()
        binaryMaskFillLayout.addLayout(fillOutsideLayout)
        binaryMaskFillLayout.addLayout(fillInsideLayout)
        fillValuesSpinBoxLayout = qt.QFormLayout()
        fillValuesSpinBoxLayout.addRow(binaryMaskFillLayout)
        fillValuesSpinBoxLayout.addRow(fillValueLayout)
        self.scriptedEffect.addOptionsWidget(fillValuesSpinBoxLayout)

        # Soft edge
        self.softEdgeMmSpinBox = slicer.qMRMLSpinBox()
        self.softEdgeMmSpinBox.setMRMLScene(slicer.mrmlScene)
        self.softEdgeMmSpinBox.setToolTip("模糊掩模边缘的高斯函数的标准差。"
                                          "值越高，边缘越柔和。")
        self.softEdgeMmSpinBox.quantity = "length"
        self.softEdgeMmSpinBox.value = 0
        self.softEdgeMmSpinBox.minimum = 0
        self.softEdgeMmSpinBox.singleStep = 0.5
        self.softEdgeMmLabel = self.scriptedEffect.addLabeledOptionsWidget("柔化边缘：", self.softEdgeMmSpinBox)
        self.softEdgeMmSpinBox.connect("valueChanged(double)", self.softEdgeMmChanged)

        # input volume selector
        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputVolumeSelector.selectNodeUponCreation = True
        self.inputVolumeSelector.addEnabled = True
        self.inputVolumeSelector.removeEnabled = True
        self.inputVolumeSelector.noneEnabled = True
        self.inputVolumeSelector.noneDisplay = "源体数据"#(Source volume)
        self.inputVolumeSelector.showHidden = False
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.inputVolumeSelector.setToolTip("遮罩数据。默认为当前源数据节点。")
        self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputVolumeChanged)

        self.inputVisibilityButton = qt.QToolButton()
        self.inputVisibilityButton.setIcon(self.invisibleIcon)
        self.inputVisibilityButton.connect('clicked()', self.onInputVisibilityButtonClicked)
        inputLayout = qt.QHBoxLayout()
        inputLayout.addWidget(self.inputVisibilityButton)
        inputLayout.addWidget(self.inputVolumeSelector)
        self.scriptedEffect.addLabeledOptionsWidget("输入数据：", inputLayout)

        # output volume selector
        self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
        self.outputVolumeSelector.selectNodeUponCreation = True
        self.outputVolumeSelector.addEnabled = True
        self.outputVolumeSelector.removeEnabled = True
        self.outputVolumeSelector.renameEnabled = True
        self.outputVolumeSelector.noneEnabled = True
        self.outputVolumeSelector.noneDisplay = "（创建新的体数据）"#noneDisplay无内容时显示： (Create new Volume)
        self.outputVolumeSelector.showHidden = False
        self.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.outputVolumeSelector.setToolTip("蒙版输出数据。它可以与累积蒙版的输入数据相同。")
        self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onOutputVolumeChanged)

        self.outputVisibilityButton = qt.QToolButton()
        self.outputVisibilityButton.setIcon(self.invisibleIcon)
        self.outputVisibilityButton.connect('clicked()', self.onOutputVisibilityButtonClicked)
        outputLayout = qt.QHBoxLayout()
        outputLayout.addWidget(self.outputVisibilityButton)
        outputLayout.addWidget(self.outputVolumeSelector)
        self.scriptedEffect.addLabeledOptionsWidget("输出数据：", outputLayout)

        # Apply button
        self.applyButton = qt.QPushButton("应用")
        self.applyButton.objectName = self.__class__.__name__ + 'Apply'
        self.applyButton.setToolTip("将分割应用为数据蒙版。一旦应用，无法执行撤销操作。")
        self.scriptedEffect.addOptionsWidget(self.applyButton)
        self.applyButton.connect('clicked()', self.onApply)

        for button in self.operationRadioButtons:
            button.connect('toggled(bool)',
                           lambda toggle, widget=self.buttonToOperationNameMap[button]: self.onOperationSelectionChanged(widget, toggle))

    def createCursor(self, widget):
        # Turn off effect-specific cursor for this effect
        return slicer.util.mainWindow().cursor

    def setMRMLDefaults(self):
        self.scriptedEffect.setParameterDefault("FillValue", "0")
        self.scriptedEffect.setParameterDefault("BinaryMaskFillValueInside", "1")
        self.scriptedEffect.setParameterDefault("BinaryMaskFillValueOutside", "0")
        self.scriptedEffect.setParameterDefault("SoftEdgeMm", "0")
        self.scriptedEffect.setParameterDefault("Operation", "FILL_OUTSIDE")

    def isVolumeVisible(self, volumeNode):
        if not volumeNode:
            return False
        volumeNodeID = volumeNode.GetID()
        lm = slicer.app.layoutManager()
        sliceViewNames = lm.sliceViewNames()
        for sliceViewName in sliceViewNames:
            sliceWidget = lm.sliceWidget(sliceViewName)
            if volumeNodeID == sliceWidget.mrmlSliceCompositeNode().GetBackgroundVolumeID():
                return True
        return False

    def updateGUIFromMRML(self):
        self.updatingGUIFromMRML = True

        self.fillValueEdit.setValue(float(self.scriptedEffect.parameter("FillValue")) if self.scriptedEffect.parameter("FillValue") else 0)
        self.binaryMaskFillOutsideEdit.setValue(float(self.scriptedEffect.parameter("BinaryMaskFillValueOutside"))
                                                if self.scriptedEffect.parameter("BinaryMaskFillValueOutside") else 0)
        self.binaryMaskFillInsideEdit.setValue(float(self.scriptedEffect.parameter("BinaryMaskFillValueInside"))
                                               if self.scriptedEffect.parameter("BinaryMaskFillValueInside") else 1)
        operationName = self.scriptedEffect.parameter("Operation")
        if operationName:
            operationButton = list(self.buttonToOperationNameMap.keys())[list(self.buttonToOperationNameMap.values()).index(operationName)]
            operationButton.setChecked(True)

        self.softEdgeMmSpinBox.setValue(float(self.scriptedEffect.parameter("SoftEdgeMm"))
                                        if self.scriptedEffect.parameter("SoftEdgeMm") else 0)

        inputVolume = self.scriptedEffect.parameterSetNode().GetNodeReference("Mask volume.InputVolume")
        self.inputVolumeSelector.setCurrentNode(inputVolume)
        outputVolume = self.scriptedEffect.parameterSetNode().GetNodeReference("Mask volume.OutputVolume")
        self.outputVolumeSelector.setCurrentNode(outputVolume)

        sourceVolume = self.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
        if inputVolume is None:
            inputVolume = sourceVolume

        self.fillValueEdit.setVisible(operationName in ["FILL_INSIDE", "FILL_OUTSIDE"])
        self.fillValueLabel.setVisible(operationName in ["FILL_INSIDE", "FILL_OUTSIDE"])
        self.binaryMaskFillInsideEdit.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
        self.fillInsideLabel.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
        self.binaryMaskFillOutsideEdit.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
        self.fillOutsideLabel.setVisible(operationName == "FILL_INSIDE_AND_OUTSIDE")
        if operationName in ["FILL_INSIDE", "FILL_OUTSIDE"]:
            if self.outputVolumeSelector.noneDisplay != "（创建新体数据）":
                self.outputVolumeSelector.noneDisplay = "（创建新体数据）"
                self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode", "vtkMRMLLabelMapVolumeNode"]
        else:
            if self.outputVolumeSelector.noneDisplay != "(Create new Labelmap Volume)":
                self.outputVolumeSelector.noneDisplay = "(Create new Labelmap Volume)"
                self.outputVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode", "vtkMRMLScalarVolumeNode"]

        self.inputVisibilityButton.setIcon(self.visibleIcon if self.isVolumeVisible(inputVolume) else self.invisibleIcon)
        self.outputVisibilityButton.setIcon(self.visibleIcon if self.isVolumeVisible(outputVolume) else self.invisibleIcon)

        self.updatingGUIFromMRML = False

    def updateMRMLFromGUI(self):
        if self.updatingGUIFromMRML:
            return
        self.scriptedEffect.setParameter("FillValue", self.fillValueEdit.value)
        self.scriptedEffect.setParameter("BinaryMaskFillValueInside", self.binaryMaskFillInsideEdit.value)
        self.scriptedEffect.setParameter("BinaryMaskFillValueOutside", self.binaryMaskFillOutsideEdit.value)
        self.scriptedEffect.parameterSetNode().SetNodeReferenceID("Mask volume.InputVolume", self.inputVolumeSelector.currentNodeID)
        self.scriptedEffect.parameterSetNode().SetNodeReferenceID("Mask volume.OutputVolume", self.outputVolumeSelector.currentNodeID)
        self.scriptedEffect.setParameter("SoftEdgeMm", self.softEdgeMmSpinBox.value)

    def activate(self):
        self.scriptedEffect.setParameter("InputVisibility", "True")

    def deactivate(self):
        if self.outputVolumeSelector.currentNode() is not self.scriptedEffect.parameterSetNode().GetSourceVolumeNode():
            self.scriptedEffect.setParameter("OutputVisibility", "False")
        slicer.util.setSliceViewerLayers(background=self.scriptedEffect.parameterSetNode().GetSourceVolumeNode())

    def onOperationSelectionChanged(self, operationName, toggle):
        if not toggle:
            return
        self.scriptedEffect.setParameter("Operation", operationName)

    def softEdgeMmChanged(self, edgeMm):
        self.scriptedEffect.setParameter("SoftEdgeMm", edgeMm)

    def getInputVolume(self):
        inputVolume = self.inputVolumeSelector.currentNode()
        if inputVolume is None:
            inputVolume = self.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
        return inputVolume

    def onInputVisibilityButtonClicked(self):
        inputVolume = self.scriptedEffect.parameterSetNode().GetNodeReference("Mask volume.InputVolume")
        sourceVolume = self.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
        if inputVolume is None:
            inputVolume = sourceVolume
        if inputVolume:
            slicer.util.setSliceViewerLayers(background=inputVolume)
            self.updateGUIFromMRML()

    def onOutputVisibilityButtonClicked(self):
        outputVolume = self.scriptedEffect.parameterSetNode().GetNodeReference("Mask volume.OutputVolume")
        if outputVolume:
            slicer.util.setSliceViewerLayers(background=outputVolume)
            self.updateGUIFromMRML()

    def onInputVolumeChanged(self):
        self.scriptedEffect.parameterSetNode().SetNodeReferenceID("Mask volume.InputVolume", self.inputVolumeSelector.currentNodeID)
        self.updateGUIFromMRML()  # node reference changes are not observed, update GUI manually

    def onOutputVolumeChanged(self):
        self.scriptedEffect.parameterSetNode().SetNodeReferenceID("Mask volume.OutputVolume", self.outputVolumeSelector.currentNodeID)
        self.updateGUIFromMRML()  # node reference changes are not observed, update GUI manually

    def fillValueChanged(self):
        self.updateMRMLFromGUI()

    def onApply(self):
        with slicer.util.tryWithErrorDisplay("Failed to apply mask to volume.", waitCursor=True):
            inputVolume = self.getInputVolume()
            outputVolume = self.outputVolumeSelector.currentNode()
            operationMode = self.scriptedEffect.parameter("Operation")
            if not outputVolume:
                # Create new node for output
                volumesLogic = slicer.modules.volumes.logic()
                scene = inputVolume.GetScene()
                if operationMode == "FILL_INSIDE_AND_OUTSIDE":
                    outputVolumeName = inputVolume.GetName() + " label"
                    outputVolume = volumesLogic.CreateAndAddLabelVolume(inputVolume, outputVolumeName)
                else:
                    outputVolumeName = inputVolume.GetName() + " masked"
                    outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)
                self.outputVolumeSelector.setCurrentNode(outputVolume)

            if operationMode in ["FILL_INSIDE", "FILL_OUTSIDE"]:
                fillValues = [self.fillValueEdit.value]
            else:
                fillValues = [self.binaryMaskFillInsideEdit.value, self.binaryMaskFillOutsideEdit.value]

            segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
            segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()

            softEdgeMm = self.scriptedEffect.doubleParameter("SoftEdgeMm")

            SegmentEditorMaskVolumeEffect.maskVolumeWithSegment(segmentationNode, segmentID, operationMode, fillValues, inputVolume, outputVolume,
                                                                softEdgeMm=softEdgeMm)

            slicer.util.setSliceViewerLayers(background=outputVolume)

            self.updateGUIFromMRML()

    @staticmethod
    def maskVolumeWithSegment(segmentationNode, segmentID, operationMode, fillValues, inputVolumeNode, outputVolumeNode, maskExtent=None, softEdgeMm=0.0):
        """
        Fill voxels of the input volume inside/outside the masking model with the provided fill value
        maskExtent: optional output to return computed mask extent (expected input is a 6-element list)
        fillValues: list containing one or two fill values. If fill mode is inside or outside then only one value is specified in the list.
          If fill mode is inside&outside then the list must contain two values: first is the inside fill, second is the outside fill value.
        """

        import vtk  # without this we get the error: UnboundLocalError: local variable 'vtk' referenced before assignment
        segmentIDs = vtk.vtkStringArray()
        segmentIDs.InsertNextValue(segmentID)
        maskVolumeNode = slicer.modules.volumes.logic().CreateAndAddLabelVolume(inputVolumeNode, "TemporaryVolumeMask")
        if not maskVolumeNode:
            logging.error("maskVolumeWithSegment failed: invalid maskVolumeNode")
            return False

        if not slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentationNode, segmentIDs, maskVolumeNode, inputVolumeNode):
            logging.error("maskVolumeWithSegment failed: ExportSegmentsToLabelmapNode error")
            slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode().GetColorNode())
            slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode())
            slicer.mrmlScene.RemoveNode(maskVolumeNode)
            return False

        if maskExtent:
            img = slicer.modules.segmentations.logic().CreateOrientedImageDataFromVolumeNode(maskVolumeNode)
            img.UnRegister(None)
            import vtkSegmentationCorePython as vtkSegmentationCore
            vtkSegmentationCore.vtkOrientedImageDataResample.CalculateEffectiveExtent(img, maskExtent, 0)

        if softEdgeMm == 0:
            # Hard edge
            maskToStencil = vtk.vtkImageToImageStencil()
            maskToStencil.ThresholdByLower(0)
            maskToStencil.SetInputData(maskVolumeNode.GetImageData())

            stencil = vtk.vtkImageStencil()

            if operationMode == "FILL_INSIDE_AND_OUTSIDE":
                # Set input to constant value
                thresh = vtk.vtkImageThreshold()
                thresh.SetInputData(inputVolumeNode.GetImageData())
                thresh.ThresholdByLower(0)
                thresh.SetInValue(fillValues[1])
                thresh.SetOutValue(fillValues[1])
                thresh.SetOutputScalarType(inputVolumeNode.GetImageData().GetScalarType())
                thresh.Update()
                stencil.SetInputData(thresh.GetOutput())
            else:
                stencil.SetInputData(inputVolumeNode.GetImageData())

            stencil.SetStencilConnection(maskToStencil.GetOutputPort())
            stencil.SetReverseStencil(operationMode == "FILL_OUTSIDE")
            stencil.SetBackgroundValue(fillValues[0])
            stencil.Update()
            outputVolumeNode.SetAndObserveImageData(stencil.GetOutput())
        else:
            # Soft edge

            thresh = vtk.vtkImageThreshold()
            maskMin = 0
            maskMax = 255
            thresh.SetOutputScalarTypeToUnsignedChar()
            thresh.SetInputData(maskVolumeNode.GetImageData())
            thresh.ThresholdByLower(0)
            thresh.SetInValue(maskMin)
            thresh.SetOutValue(maskMax)
            thresh.Update()

            gaussianFilter = vtk.vtkImageGaussianSmooth()
            spacing = maskVolumeNode.GetSpacing()
            standardDeviationPixel = [1.0, 1.0, 1.0]
            for idx in range(3):
                standardDeviationPixel[idx] = softEdgeMm / spacing[idx]
            gaussianFilter.SetInputConnection(thresh.GetOutputPort())
            gaussianFilter.SetStandardDeviations(*standardDeviationPixel)
            # Do not truncate the Gaussian kernel at the default 1.5 sigma,
            # because it would result in edge artifacts.
            # Larger value results in less edge artifact but increased computation time,
            # so 3.0 is a good tradeoff.
            gaussianFilter.SetRadiusFactor(3.0)
            gaussianFilter.Update()

            import vtk.util.numpy_support
            maskImage = gaussianFilter.GetOutput()
            nshape = tuple(reversed(maskImage.GetDimensions()))
            maskArray = vtk.util.numpy_support.vtk_to_numpy(maskImage.GetPointData().GetScalars()).reshape(nshape)
            # Normalize mask with the actual min/max values.
            # Gaussian output is not always exactly the original minimum and maximum, so we get the actual min/max values.
            maskMin = maskArray.min()
            maskMax = maskArray.max()
            mask = (maskArray.astype(float) - maskMin) / float(maskMax - maskMin)

            inputArray = slicer.util.arrayFromVolume(inputVolumeNode)

            if operationMode == "FILL_INSIDE_AND_OUTSIDE":
                # Rescale the smoothed mask
                resultArray = fillValues[0] + (fillValues[1] - fillValues[0]) * mask[:]
            else:
                # Compute weighted average between blanked out and input volume
                if operationMode == "FILL_INSIDE":
                    mask = 1.0 - mask
                resultArray = inputArray[:] * mask[:] + float(fillValues[0]) * (1.0 - mask[:])

            slicer.util.updateVolumeFromArray(outputVolumeNode, resultArray.astype(inputArray.dtype))

        # Set the same geometry and parent transform as the input volume
        ijkToRas = vtk.vtkMatrix4x4()
        inputVolumeNode.GetIJKToRASMatrix(ijkToRas)
        outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
        inputVolumeNode.SetAndObserveTransformNodeID(inputVolumeNode.GetTransformNodeID())

        slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode().GetColorNode())
        slicer.mrmlScene.RemoveNode(maskVolumeNode.GetDisplayNode())
        slicer.mrmlScene.RemoveNode(maskVolumeNode)
        return True
