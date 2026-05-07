# 3D Model Files

The original 3D model files in this repository were too large for convenient distribution through GitHub.

To make them easier to upload, download, and store, each model has been:

1. Compressed into a `.7z` archive using 7-Zip
2. Split into multiple 10 MB parts

The files will look similar to this:

```text
Thesis/3D_Models
├── model_1
       ├── model_1.7z.001
       ├── model_1.7z.002
       ├── model_1.7z.003
       ...
├── model_2
       ├── model_2.7z.001
       ├── model_2.7z.002
       ├── model_2.7z.003
       ...
...
└── README.md
```

All parts are required to reconstruct the original archive.

---

# Requirements

To reconstruct the original files, you will need 7-Zip or compatible archive software.

## Windows

Install 7-Zip:

https://www.7-zip.org/

## Linux

Install p7zip:

```bash
sudo apt install p7zip-full
```

## macOS

Install p7zip using Homebrew:

```bash
brew install p7zip
```

---

# How to Merge and Extract the Files

## Windows (Using 7-Zip)

### Step 1 — Download All Parts

Download every split file and place them in the same folder.

---

### Step 2 — Merge and Extract

Right-click the first file:

```text
model.7z.001
```

Then choose:

```text
7-Zip → Extract Here
```

or

```text
7-Zip → Extract to "model\"
```

7-Zip will automatically:

- Detect all split parts
- Merge the archive
- Reconstruct the original `.7z` file internally
- Extract the original 3D model

No manual merging is required on Windows.

---

# Linux / macOS Instructions

## Step 1 — Download All Parts

Make sure all split files are in the same directory.

---

## Step 2 — Merge the Split Files

Open a terminal in the folder containing the files and run:

```bash
cat model.7z.* > model.7z
```

This combines all parts into the original `.7z` archive.

---

## Step 3 — Extract the Archive

Run:

```bash
7z x model.7z
```

The original 3D model file will then be extracted.

---

# Important Notes

- Do NOT rename any split files
- Do NOT remove or skip any parts
- All parts must be located in the same folder
- Always open/extract the `.001` file on Windows
- If one part is missing or corrupted, extraction will fail

---
