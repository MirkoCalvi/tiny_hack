using System.Collections.Generic;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

/// <summary>
/// Draws a simple grid of slot meshes based on the dimensions reported by the attached Level2Manager.
/// Useful both in play mode and edit mode to visualise the Rota board.
/// </summary>
[ExecuteAlways]
[DisallowMultipleComponent]
public class BoardSlotRenderer : MonoBehaviour
{
    [SerializeField] Level2Manager levelManager;
    [SerializeField] GameObject slotPrefab;
    [SerializeField] Vector2 slotScale = new Vector2(0.9f, 0.9f);
    [SerializeField] float slotHeight;
    [SerializeField] Color slotColor = new Color(0.1f, 0.6f, 1f, 0.35f);
    [SerializeField] bool regenerateOnValidate = true;

    readonly List<GameObject> spawnedSlots = new();

    void OnEnable()
    {
        RebuildSlots();
    }

    void OnDisable()
    {
        ClearSlots();
    }

#if UNITY_EDITOR
    void OnValidate()
    {
        if (!regenerateOnValidate)
        {
            return;
        }

        if (!isActiveAndEnabled)
        {
            return;
        }

#if UNITY_EDITOR
        EditorApplication.delayCall += () =>
        {
            if (this == null)
            {
                return;
            }
            RebuildSlots();
        };
#endif
    }
#endif

    /// <summary>
    /// Clears existing slot instances and rebuilds them from the current board settings.
    /// </summary>
    public void RebuildSlots()
    {
        ClearSlots();

        var manager = ResolveManager();
        if (manager == null)
        {
            return;
        }

        var size = manager.BoardDimension;
        for (var y = 0; y < size; y++)
        {
            for (var x = 0; x < size; x++)
            {
                var cell = new Vector2Int(x, y);
                var position = manager.GetCellWorldCenter(cell, slotHeight);
                var slot = CreateSlot(manager, cell, position);
                spawnedSlots.Add(slot);
            }
        }
    }

    /// <summary>
    /// Instantiates a slot prefab (or fallback quad) for a single cell and tints it for clarity.
    /// </summary>
    GameObject CreateSlot(Level2Manager manager, Vector2Int cell, Vector3 position)
    {
        GameObject slot;
        if (slotPrefab != null)
        {
            slot = Instantiate(slotPrefab, position, Quaternion.identity, transform);
        }
        else
        {
            slot = GameObject.CreatePrimitive(PrimitiveType.Quad);
            slot.transform.SetPositionAndRotation(position, Quaternion.Euler(90f, 0f, 0f));
            if (slot.TryGetComponent<Collider>(out var collider))
            {
                if (Application.isPlaying)
                {
                    Destroy(collider);
                }
                else
                {
                    DestroyImmediate(collider);
                }
            }
            slot.transform.SetParent(transform, true);
        }

        slot.name = $"Slot_{cell.x}_{cell.y}";
        var cellSize = manager.CellDimensions;
        if (slotPrefab == null)
        {
            var newScale = new Vector3(
                Mathf.Max(0.001f, cellSize.x * slotScale.x),
                Mathf.Max(0.001f, cellSize.y * slotScale.y),
                slot.transform.localScale.z);
            slot.transform.localScale = newScale;
        }

        if (slot.TryGetComponent<Renderer>(out var renderer))
        {
            var material = Application.isPlaying ? renderer.material : renderer.sharedMaterial;
            if (material != null && material.HasProperty("_Color"))
            {
                material.color = slotColor;
            }
        }

        return slot;
    }

    /// <summary>
    /// Removes all generated slot objects so they can be rebuilt cleanly.
    /// </summary>
    void ClearSlots()
    {
        for (var i = spawnedSlots.Count - 1; i >= 0; i--)
        {
            var slot = spawnedSlots[i];
            if (slot == null)
            {
                continue;
            }

            if (Application.isPlaying)
            {
                Destroy(slot);
            }
            else
            {
                DestroyImmediate(slot);
            }
        }
        spawnedSlots.Clear();
    }

    /// <summary>
    /// Finds the Level2Manager this renderer should follow.
    /// </summary>
    Level2Manager ResolveManager()
    {
        if (levelManager != null)
        {
            return levelManager;
        }
        levelManager = GetComponentInParent<Level2Manager>();
        if (levelManager == null)
        {
            levelManager = FindObjectOfType<Level2Manager>();
        }
        return levelManager;
    }
}
