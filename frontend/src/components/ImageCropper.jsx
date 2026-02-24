import { useState, useRef, useCallback } from 'react';
import ReactCrop from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Slider } from './ui/slider';
import { RotateCcw, ZoomIn, ZoomOut, Check, X, Crop } from 'lucide-react';

const ImageCropper = ({ 
  imageSrc, 
  onCropComplete, 
  onCancel,
  aspectRatio = 1, // 1:1 square by default
  circularCrop = false,
  title = "Recortar Imagem"
}) => {
  const [crop, setCrop] = useState({
    unit: '%',
    width: 80,
    height: 80,
    x: 10,
    y: 10,
  });
  const [completedCrop, setCompletedCrop] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const imgRef = useRef(null);

  const onImageLoad = useCallback((e) => {
    const { width, height } = e.currentTarget;
    
    // Calculate initial crop to center
    const cropWidth = Math.min(80, (height / width) * 80);
    const cropHeight = aspectRatio ? cropWidth / aspectRatio : cropWidth;
    
    setCrop({
      unit: '%',
      width: cropWidth,
      height: Math.min(cropHeight, 80),
      x: (100 - cropWidth) / 2,
      y: (100 - Math.min(cropHeight, 80)) / 2,
    });
  }, [aspectRatio]);

  const getCroppedImg = useCallback(async () => {
    if (!completedCrop || !imgRef.current) return null;

    const image = imgRef.current;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) return null;

    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    // Set canvas size to the cropped area
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = completedCrop.width * scaleX * pixelRatio;
    canvas.height = completedCrop.height * scaleY * pixelRatio;

    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    ctx.imageSmoothingQuality = 'high';

    // Apply rotation if any
    if (rotation !== 0) {
      ctx.translate(canvas.width / (2 * pixelRatio), canvas.height / (2 * pixelRatio));
      ctx.rotate((rotation * Math.PI) / 180);
      ctx.translate(-canvas.width / (2 * pixelRatio), -canvas.height / (2 * pixelRatio));
    }

    ctx.drawImage(
      image,
      completedCrop.x * scaleX,
      completedCrop.y * scaleY,
      completedCrop.width * scaleX,
      completedCrop.height * scaleY,
      0,
      0,
      completedCrop.width * scaleX,
      completedCrop.height * scaleY
    );

    // If circular crop, apply mask
    if (circularCrop) {
      ctx.globalCompositeOperation = 'destination-in';
      ctx.beginPath();
      ctx.arc(
        canvas.width / (2 * pixelRatio),
        canvas.height / (2 * pixelRatio),
        Math.min(canvas.width, canvas.height) / (2 * pixelRatio),
        0,
        2 * Math.PI
      );
      ctx.fill();
    }

    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(null);
            return;
          }
          resolve(blob);
        },
        'image/png',
        1
      );
    });
  }, [completedCrop, rotation, circularCrop]);

  const handleSave = async () => {
    const croppedBlob = await getCroppedImg();
    if (croppedBlob) {
      onCropComplete(croppedBlob);
    }
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  return (
    <Dialog open={true} onOpenChange={() => onCancel()}>
      <DialogContent className="max-w-2xl bg-neutral-900 border-neutral-800">
        <DialogHeader>
          <DialogTitle className="text-white flex items-center gap-2">
            <Crop className="h-5 w-5 text-[#FFD600]" />
            {title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Preview area */}
          <div className="relative bg-neutral-800 rounded-lg p-4 flex items-center justify-center min-h-[300px] max-h-[400px] overflow-hidden">
            <ReactCrop
              crop={crop}
              onChange={(c) => setCrop(c)}
              onComplete={(c) => setCompletedCrop(c)}
              aspect={aspectRatio}
              circularCrop={circularCrop}
              className="max-h-[350px]"
            >
              <img
                ref={imgRef}
                src={imageSrc}
                alt="Imagem para recortar"
                onLoad={onImageLoad}
                style={{
                  transform: `scale(${zoom}) rotate(${rotation}deg)`,
                  maxHeight: '350px',
                  maxWidth: '100%',
                  objectFit: 'contain',
                }}
                crossOrigin="anonymous"
              />
            </ReactCrop>
          </div>

          {/* Controls */}
          <div className="space-y-4 px-2">
            {/* Zoom control */}
            <div className="flex items-center gap-4">
              <ZoomOut className="h-4 w-4 text-neutral-400" />
              <Slider
                value={[zoom * 100]}
                onValueChange={(v) => setZoom(v[0] / 100)}
                min={50}
                max={200}
                step={5}
                className="flex-1"
              />
              <ZoomIn className="h-4 w-4 text-neutral-400" />
              <span className="text-sm text-neutral-400 w-12">{Math.round(zoom * 100)}%</span>
            </div>

            {/* Rotation button */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleRotate}
                className="border-neutral-700 text-neutral-300 hover:bg-neutral-800"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Girar 90°
              </Button>
              <span className="text-sm text-neutral-400">Rotação: {rotation}°</span>
            </div>
          </div>

          {/* Tips */}
          <div className="bg-neutral-800/50 rounded-lg p-3 text-sm text-neutral-400">
            <p>💡 Dica: Arraste os cantos da área de seleção para ajustar o recorte. Use o zoom para ajustar o tamanho da imagem.</p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            className="border-neutral-700 text-neutral-300 hover:bg-neutral-800"
          >
            <X className="h-4 w-4 mr-2" />
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            className="bg-[#FFD600] text-black hover:bg-[#FFD600]/90"
          >
            <Check className="h-4 w-4 mr-2" />
            Aplicar Recorte
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ImageCropper;
