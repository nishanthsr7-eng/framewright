# Labeling frames for the segmentation eval

1. `python evals/extract_label_frames.py` writes 20 frames per set to
   `evals/labels/{anime,live-action}/images/`.
2. For each `images/<name>.png`, save a mask as `masks/<name>.png` in the same set folder:
   - same width and height as the frame
   - grayscale (or RGB): **white = subject, black = everything else**
   - subject = the main person or character the edit would cut out. Hair counts; held objects count;
     shadows and motion-blur trails do not.
   - frame with no clear subject: delete the image instead of labeling it.
3. Run the eval:
   `uv run --directory servers/assets/subject_extractor python ../../../evals/eval_segmentation.py --real`

## GIMP (about 2–4 min per frame)
1. Open the frame. Select the subject with **Foreground Select** (or Paths for hard edges),
   then refine with Free Select.
2. Layer › New Layer, fill black. Edit › Fill selection with white.
3. Hide the original, then File › Export As `masks/<name>.png`.

## CVAT (faster for many frames)
1. Create a task with the 20 images and one label `subject`. Draw polygons, or use the AI tools.
2. Export as **Segmentation mask 1.1**. Copy `SegmentationClass/*.png` into `masks/`.
   Any non-black colour counts as subject.

Frames come from `samples/` and stay local (`evals/labels/` is gitignored).
