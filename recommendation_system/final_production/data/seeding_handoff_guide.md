# Backend Seeding Handoff Guide: Products & Raw Materials

This guide provides the necessary technical details, database mappings, and implementation guidelines for the backend team to seed the database using the newly generated database-aligned JSON data files.

---

## 1. Seeding Data Files

Two clean, pre-validated JSON files are located in the `data/` directory. They align 100% with the columns, constraints, and data types of the `Products` and `RawMaterials` SQL Server tables.

1. **Products Seeding Dataset**:
   - **Path**: `data/products_db_seeding.json`
   - **Record Count**: 200 products
   - **Target Database Table**: `Products`
2. **Raw Materials Seeding Dataset**:
   - **Path**: `data/raw_materials_db_seeding.json`
   - **Record Count**: 100 materials
   - **Target Database Table**: `RawMaterials`

---

## 2. Table Mappings & Schema Details

### A. Products Table (`Products`)
The products JSON dataset maps to the database columns as follows:

| Database Column | JSON Key | Data Type | Seeding Strategy / Meaning |
| :--- | :--- | :--- | :--- |
| **`Id`** | `Id` | `int` | Primary Key (original mock catalog index: `1` to `200`). |
| **`Name`** | `Name` | `nvarchar(100)` | Name of the product. |
| **`Description`** | `Description` | `nvarchar(2000)`| Detailed description of the product. |
| **`Price`** | `Price` | `decimal(18,2)` | Product price. |
| **`CategoryId`** | `CategoryId` | `int` | **Foreign Key** corresponding to the `Categories` lookup table (details below). |
| **`BusinessOwnerProfileId`** | `BusinessOwnerProfileId` | `int` | Mapped to `1` (Assumes a default business owner exists in the database). |
| **`Status`** | `Status` | `int` | Mapped to `1` (Active/Approved). |
| **`StockQuantity`** | `StockQuantity` | `int` | Defaulted to `100`. |
| **`IsVisible`** | `IsVisible` | `bool` | Defaulted to `true`. |
| **`IsDeleted`** | `IsDeleted` | `bool` | Defaulted to `false`. |
| **`CreatedAt`** | `CreatedAt` | `datetime2` | Timestamp when records were generated (UTC format: `YYYY-MM-DDTHH:MM:SSZ`). |
| **`ApprovedAt`** | `ApprovedAt` | `datetime2` | UTC Timestamp (matches `CreatedAt` to avoid null constraint issues). |
| **`ApprovedBy`** | `ApprovedBy` | `nvarchar(max)` | Mapped to `"SystemSeeder"`. |
| *Other Nullable Columns* | *Various* | *Various* | Populated with `null` or `0` for metrics (e.g. `AvgRating`, `ViewCount`, `RevenueTotal`). |

> [!IMPORTANT]
> **CategoryId Association Mapping (FK Constraint)**
> The original text-based product categories have been mapped to their corresponding database Foreign Key integer values:
> - `"Fashion & Accessories"` &rarr; **`1`**
> - `"Handmade & Crafts"` &rarr; **`2`**
> - `"Natural & Beauty Products"` &rarr; **`3`**
> 
> *Ensure that the `Categories` lookup table has these records created with these matching IDs before running the product seeder.*

---

### B. Raw Materials Table (`RawMaterials`)
The raw materials JSON dataset maps to the database columns as follows:

| Database Column | JSON Key | Data Type | Seeding Strategy / Meaning |
| :--- | :--- | :--- | :--- |
| **`Id`** | `Id` | `int` | Primary Key (original mock catalog index: `1` to `100`). |
| **`Name`** | `Name` | `nvarchar(200)` | Name of the raw material. |
| **`Description`** | `Description` | `nvarchar(1000)`| Detailed description of the material. |
| **`Price`** | `Price` | `decimal(18,2)` | Raw material price. |
| **`Unit`** | `Unit` | `nvarchar(50)` | Unit of measurement, defaulted to `"pcs"`. |
| **`MinimumOrderQuantity`**| `MinimumOrderQuantity`| `int` | Defaulted to `1`. |
| **`StockQuantity`** | `StockQuantity` | `int` | Defaulted to `100`. |
| **`IsAvailable`** | `IsAvailable` | `bool` | Defaulted to `true`. |
| **`Category`** | `Category` | `nvarchar(100)` | Category name stored directly as string (e.g. `"Natural & Beauty Products"`). |
| **`SupplierId`** | `SupplierId` | `int` | Mapped to `1` (Assumes a default supplier exists in the database). |
| **`CreatedAt`** | `CreatedAt` | `datetime2` | UTC Timestamp. |
| **`IsDeleted`** | `IsDeleted` | `bool` | Defaulted to `false`. |
| **`OrderFrequency`** | `OrderFrequency` | `int` | Defaulted to `0`. |
| **`PriceTrend`** | `PriceTrend` | `nvarchar(max)` | Defaulted to empty string `""`. |
| *Other Nullable Columns* | *Various* | *Various* | Populated with `null` (e.g. `PictureUrl`, `UpdatedAt`, `DeletedAt`). |

---

## 3. How to Implement Seeding in Backend (.NET EF Core Example)

For a typical ASP.NET Core EF Core backend, the database team can load the JSON files and seed them within the `DbContext` class or a custom migration class:

### Step A: Model Class Validation
Ensure the Entity Framework Core models have matching properties. For example, for the product entity:
```csharp
public class Product 
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string Description { get; set; }
    public decimal Price { get; set; }
    public int CategoryId { get; set; }
    public int BusinessOwnerProfileId { get; set; }
    public int Status { get; set; }
    public int StockQuantity { get; set; }
    public bool IsVisible { get; set; }
    public bool IsDeleted { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? ApprovedAt { get; set; }
    public string ApprovedBy { get; set; }
    // ... nullable properties
}
```

### Step B: Seeding Logic inside `OnModelCreating`
The backend team can read these JSON files directly inside their `DbContext`:

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;

public class ApplicationDbContext : DbContext
{
    public DbSet<Product> Products { get; set; }
    public DbSet<RawMaterial> RawMaterials { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // 1. Seed Categories first (to satisfy Products FK)
        modelBuilder.Entity<Category>().HasData(
            new Category { Id = 1, Name = "Fashion & Accessories" },
            new Category { Id = 2, Name = "Handmade & Crafts" },
            new Category { Id = 3, Name = "Natural & Beauty Products" }
        );

        // 2. Seed Products
        var productsJson = File.ReadAllText("PathTo/products_db_seeding.json");
        var products = JsonSerializer.Deserialize<List<Product>>(productsJson);
        if (products != null)
        {
            modelBuilder.Entity<Product>().HasData(products);
        }

        // 3. Seed Raw Materials
        var materialsJson = File.ReadAllText("PathTo/raw_materials_db_seeding.json");
        var materials = JsonSerializer.Deserialize<List<RawMaterial>>(materialsJson);
        if (materials != null)
        {
            modelBuilder.Entity<RawMaterial>().HasData(materials);
        }
    }
}
```

> [!TIP]
> **Identity Insert Rule**
> When executing seed migrations, Entity Framework Core automatically handles enabling `IDENTITY_INSERT` on SQL Server since explicit values for `Id` are provided in the HasData configuration. If seeding using raw SQL or custom seed scripts, the backend team must issue `SET IDENTITY_INSERT TableName ON;` before running insert queries.

---

## 4. The Interactions Data (Important Architectural Note)

In the local recommendation system codebase, customer behavior signals (clicks, views, purchases, reorders) are aggregated into a unified format represented by the local `interactions` schema (defined as the `Interaction` model in `shared/database/models.py`).

However, in the production database, these records map to standard transactional tables rather than a single log table. The backend team has two options for integrating and seeding this data:

### Option A: Implement a Unified Telemetry/Interactions Table (Highly Recommended)
We recommend creating a unified `Interactions` table in SQL Server. This serves as an optimized event telemetry log. The local machine learning training pipeline is pre-configured to query this table directly.

#### Schema for Unified `Interactions` Table:
| Database Column | Data Type | Nullable | Source Keys / Meaning |
| :--- | :--- | :--- | :--- |
| **`interaction_id`** | `int` (PK, Identity) | No | Auto-incremented ID. |
| **`user_type`** | `varchar(20)` | No | `"customer"` or `"owner"` |
| **`user_id`** | `int` | No | Foreign Key matching `AspNetUsers.Id` (for customers) or `BusinessOwnerProfile.Id` (for owners). |
| **`item_id`** | `int` | No | Foreign Key matching `Products.Id` (for customer product views/clicks) or `RawMaterials.Id` (for owner material views/reorders). |
| **`item_type`** | `varchar(20)` | No | `"product"` (B2C) or `"raw_material"` (B2B) |
| **`interaction_type`**| `varchar(50)` | No | `"view"`, `"click"`, `"purchase"`, `"add_to_cart"`, `"reorder"` |
| **`category`** | `varchar(100)` | No | Category name string. |
| **`quantity`** | `int` | No | Quantity involved in the action (typically `1` for views/clicks, or larger for orders). |
| **`price`** | `float` | No | Mapped price at the time of interaction. |
| **`interaction_timestamp`**| `datetime` | No | Timestamp of event (UTC). |

---

### Option B: Map to Existing Transactional Tables
If the backend team prefers to store interaction signals across their standard transactional tables, the mock records should be distributed as follows:

1. **Purchases (`interaction_type == "purchase"`)**:
   - Seed into `CustomerOrders` & `CustomerOrderItems` (B2C products).
   - Seed into `MaterialOrders` & `MaterialOrderItems` (B2B raw materials).
2. **Cart Additions (`interaction_type == "add_to_cart"`)**:
   - Seed into `CustomerCarts` & `CustomerCartItems` (B2C products).
   - Seed into `MaterialBaskets` & `MaterialBasketItems` (B2B raw materials).
3. **Views and Clicks (`"view"` / `"click"`)**:
   - Seed into `UserActionLogs` (general action audit table).

---

## 5. Critical Database Performance & Size Warnings

> [!CAUTION]
> **DO NOT Use EF Core `HasData()` Seeding for Interactions!**
> - The B2C dataset (`customer_interactions.json`) contains **660,000 records**.
> - The B2B dataset (`owner_interactions.json`) contains **440,000 records**.
> 
> Seed data declared via EF Core `HasData()` is compiled directly into C# migration classes. Trying to compile a migration with over **1.1 million rows** will result in a multi-gigabyte class file, leading to memory exhaustion, severe CLI lag, and compiler crashes.

### Recommended Bulk Loading Strategies:
To seed interactions successfully, the backend team should use one of the following high-performance methods:

1. **SQL Bulk Insert (Recommended for speed)**:
   Upload the JSON/CSV to SQL Server and run a bulk insert query:
   ```sql
   -- Example SQL Bulk Load
   BULK INSERT Interactions
   FROM 'C:\path_to\customer_interactions.csv'
   WITH (
       FIELDTERMINATOR = ',',
       ROWTERMINATOR = '\n',
       FIRSTROW = 2
   );
   ```

2. **C# SqlBulkCopy Utility (Recommended for .NET service layer)**:
   Use `SqlBulkCopy` in a custom startup initializer script to stream the JSON records in chunks:
   ```csharp
   // High-performance streaming batch seed
   using (var bulkCopy = new SqlBulkCopy(connectionString))
   {
       bulkCopy.DestinationTableName = "Interactions";
       bulkCopy.BatchSize = 5000;
       // Read JSON in chunked stream and write to DB
       await bulkCopy.WriteToServerAsync(dataReader);
   }
   ```

3. **Subset Seeding**:
   If the backend team only needs to verify database pipelines, they can take a subset of the files (e.g. the first 1,000 rows of each JSON file) for lightweight database testing.

