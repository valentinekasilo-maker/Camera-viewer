import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import axios from "axios";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FaCloudUploadAlt, FaTimes } from "react-icons/fa";
import { LuLoader } from "react-icons/lu";
import { toast } from "sonner";

interface AddIdentityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  defaultObjectClass?: string;
}

const SUPPORTED_CLASSES = [
  { value: "person", label: "Person" },
  { value: "car", label: "Car / SUV" },
  { value: "motorcycle", label: "Motorcycle" },
  { value: "bicycle", label: "Bicycle" },
  { value: "truck", label: "Truck / Pickup" },
  { value: "bus", label: "Bus / Van" },
  { value: "dog", label: "Dog" },
  { value: "cat", label: "Cat" },
  { value: "backpack", label: "Backpack / Bag" },
  { value: "package", label: "Package / Box" },
];

const CATEGORIES = [
  "Home Member",
  "Family",
  "Personal Vehicle",
  "Family Car",
  "Delivery Vehicle",
  "Frequent Visitor",
  "Pet",
  "Equipment",
  "Important Item",
  "General",
];

export function AddIdentityDialog({
  open,
  onOpenChange,
  onSuccess,
  defaultObjectClass = "car",
}: AddIdentityDialogProps) {
  const { t } = useTranslation(["views/identities", "common"]);

  const [name, setName] = useState("");
  const [objectClass, setObjectClass] = useState(defaultObjectClass);
  const [category, setCategory] = useState("Personal Vehicle");
  const [color, setColor] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);

      const newPreviews = filesArray.map((file) => URL.createObjectURL(file));
      setPreviews((prev) => [...prev, ...newPreviews]);
    }
  };

  const removeFile = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Identity name is required");
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("name", name.trim());
      formData.append("object_class", objectClass);
      formData.append("category", category);
      if (color.trim()) formData.append("color", color.trim());
      if (description.trim()) formData.append("description", description.trim());
      if (notes.trim()) formData.append("notes", notes.trim());

      selectedFiles.forEach((file) => {
        formData.append("photos", file);
      });

      await axios.post("identities", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast.success(`Identity "${name}" enrolled successfully`);
      // Reset form
      setName("");
      setColor("");
      setDescription("");
      setNotes("");
      setSelectedFiles([]);
      setPreviews([]);
      onOpenChange(false);
      onSuccess();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to enroll identity");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[620px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            {t("modal.add_title")}
          </DialogTitle>
          <DialogDescription>{t("modal.add_subtitle")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="name" className="text-xs font-semibold">
              {t("modal.name_label")} *
            </Label>
            <Input
              id="name"
              placeholder="e.g. White Toyota Harrier, Valence's Car, John"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="bg-secondary/40"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Object Class */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                {t("modal.object_class_label")} *
              </Label>
              <Select
                value={objectClass}
                onValueChange={(val) => {
                  setObjectClass(val);
                  if (val === "person") setCategory("Home Member");
                  else if (["car", "motorcycle", "truck", "bus"].includes(val))
                    setCategory("Personal Vehicle");
                  else if (["dog", "cat"].includes(val)) setCategory("Pet");
                }}
              >
                <SelectTrigger className="bg-secondary/40">
                  <SelectValue placeholder="Select class" />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED_CLASSES.map((cls) => (
                    <SelectItem key={cls.value} value={cls.value}>
                      {cls.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Category */}
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">
                {t("modal.category_label")}
              </Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="bg-secondary/40">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Color */}
            <div className="space-y-1.5">
              <Label htmlFor="color" className="text-xs font-semibold">
                {t("modal.color_label")}
              </Label>
              <Input
                id="color"
                placeholder="e.g. Pearl White, Navy Blue, Silver"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="bg-secondary/40"
              />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="desc" className="text-xs font-semibold">
                {t("modal.description_label")}
              </Label>
              <Input
                id="desc"
                placeholder="e.g. Owner Valence's SUV"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="bg-secondary/40"
              />
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-xs font-semibold">
              {t("modal.notes_label")}
            </Label>
            <Textarea
              id="notes"
              placeholder="e.g. Parked in main driveway. Monitored at Gate & Entrance."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="bg-secondary/40 text-xs"
            />
          </div>

          {/* Multi-Photo Reference Upload */}
          <div className="space-y-2 border-t border-border/40 pt-3">
            <Label className="text-xs font-semibold">
              {t("modal.photos_label")}
            </Label>
            <div className="relative border-2 border-dashed border-border/60 hover:border-primary/50 rounded-xl p-4 text-center bg-secondary/10 transition-colors">
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileSelect}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <FaCloudUploadAlt className="mx-auto text-3xl text-muted-foreground/60 mb-1" />
              <p className="text-xs text-muted-foreground font-medium">
                {t("modal.drop_photos")}
              </p>
              <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                PNG, JPG, WEBP (Multiple angles & lighting improve recognition)
              </p>
            </div>

            {/* Photo Previews */}
            {previews.length > 0 && (
              <div className="flex flex-wrap gap-2.5 pt-2">
                {previews.map((src, index) => (
                  <div
                    key={index}
                    className="relative group h-16 w-16 rounded-lg overflow-hidden border border-border/60 bg-black/40"
                  >
                    <img
                      src={src}
                      alt={`Preview ${index + 1}`}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="absolute top-1 right-1 bg-destructive/90 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <FaTimes className="text-[10px]" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t("modal.cancel")}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <LuLoader className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                t("modal.save")
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
