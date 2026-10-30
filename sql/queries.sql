-- 1. WHERE: announcements for an exact department (parameter: department name).
SELECT a.id, a.title, d.name AS department
FROM announcements AS a
JOIN departments AS d ON d.id = a.department_id
WHERE d.name = ?;

-- 2. WHERE: title search (parameter: a LIKE pattern such as '%VPN%').
SELECT id, title, priority
FROM announcements
WHERE title LIKE ?;

-- 3. JOIN: all announcements with their department names.
SELECT a.id, a.title, d.name AS department
FROM announcements AS a
JOIN departments AS d ON d.id = a.department_id;

-- 4. JOIN: announcements active on a date (supply the date twice).
SELECT a.id, a.title, d.name AS department
FROM announcements AS a
JOIN departments AS d ON d.id = a.department_id
WHERE a.is_published = 1 AND a.publish_date <= ? AND a.expiry_date >= ?;

-- 5. Aggregate: total and published announcement counts.
SELECT COUNT(*) AS total_count,
       SUM(CASE WHEN is_published = 1 THEN 1 ELSE 0 END) AS published_count
FROM announcements;

-- 6. Aggregate: minimum, maximum, and average priority.
SELECT MIN(priority) AS minimum_priority,
       MAX(priority) AS maximum_priority,
       AVG(priority) AS average_priority
FROM announcements;

-- 7. GROUP BY: number of announcements in each department.
SELECT d.name, COUNT(a.id) AS announcement_count
FROM departments AS d
LEFT JOIN announcements AS a ON a.department_id = d.id
GROUP BY d.id, d.name;

-- 8. GROUP BY: totals for each priority.
SELECT priority, COUNT(*) AS announcement_count
FROM announcements
GROUP BY priority;

-- 9. HAVING: departments with at least the supplied number of announcements.
SELECT d.name, COUNT(a.id) AS announcement_count
FROM departments AS d
JOIN announcements AS a ON a.department_id = d.id
GROUP BY d.id, d.name
HAVING COUNT(a.id) >= ?;

-- 10. HAVING: priorities with a count at or above the supplied threshold.
SELECT priority, COUNT(*) AS announcement_count
FROM announcements
GROUP BY priority
HAVING COUNT(*) >= ?;

-- 11. Date-filtered listing (parameter: YYYY-MM-DD).
SELECT id, title, publish_date, expiry_date
FROM announcements
WHERE is_published = 1 AND publish_date <= ? AND expiry_date >= ?
ORDER BY priority DESC;

-- 12. Expired published announcements (parameter: YYYY-MM-DD).
SELECT id, title, expiry_date
FROM announcements
WHERE is_published = 1 AND expiry_date < ?
ORDER BY expiry_date DESC;
