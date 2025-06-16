#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database module for fast chapter indexing in EPUB generation.
Uses peewee ORM with SQLite for efficient chapter heading detection.
Following the pattern from the original books_manager implementation.
"""

import os
import re
import uuid
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Callable, Pattern
from datetime import datetime
import tempfile

from peewee import (
    Model, SqliteDatabase, CharField, IntegerField, 
    TextField, DateTimeField, BooleanField, AutoField,
    Check, chunked, fn
)

# Database instance - use in-memory for speed
db = SqliteDatabase(':memory:', pragmas={'journal_mode': 'memory'})


class BaseModel(Model):
    """Base model with common configuration"""
    class Meta:
        database = db


class BookLine(BaseModel):
    """Each line of the book with metadata"""
    book_line_id = CharField(primary_key=True, unique=True, max_length=50)
    book_id = CharField(max_length=50, default='temp_book')
    book_line_number = IntegerField(default=1, constraints=[Check('book_line_number > 0')], null=False)
    date = DateTimeField(default=datetime.now)
    translated = BooleanField(default=True)  # Already translated
    original_line_variation_id = CharField(max_length=50, null=False)
    active_line_variation_id = CharField(max_length=50, null=True)
    book_line_title = CharField(max_length=255, null=True)  # For chapter titles
    is_chapter_heading = BooleanField(default=False, index=True)
    chapter_number = IntegerField(null=True, index=True)

    class Meta:
        table_name = 'BookLine'
        indexes = (
            (('book_id', 'book_line_number'), True),
            (('is_chapter_heading', 'chapter_number'), False),
        )


class LineVariation(BaseModel):
    """The actual text content of each line"""
    line_variation_id = CharField(primary_key=True, unique=True, max_length=50)
    book_id = CharField(max_length=50, default='temp_book', null=False)
    book_line_id = CharField(max_length=50, null=False)
    book_line_number = IntegerField(default=1, constraints=[Check('book_line_number > 0')], null=False)
    language = CharField(null=True, default='english')
    category = CharField(choices=[("original", "Original"), ("modified", "Modified"), ("translation", "Translation")], default="translation")
    date = DateTimeField(default=datetime.now)
    text_content = TextField(null=True)
    
    class Meta:
        table_name = 'LineVariation'
        indexes = (
            (('book_id', 'book_line_number'), False),
        )


def setup_database() -> None:
    """Initialize database and create tables"""
    try:
        if db.is_closed():
            db.connect()
        db.create_tables([BookLine, LineVariation], safe=True)
    except Exception as e:
        # If already connected, just ensure tables exist
        if "already opened" in str(e):
            db.create_tables([BookLine, LineVariation], safe=True)
        else:
            raise RuntimeError(f"Failed to setup database: {e}")


def close_database() -> None:
    """Close database connection"""
    try:
        if not db.is_closed():
            db.close()
    except Exception:
        # Ignore errors during close
        pass


def import_text_to_db(text: str, book_id: str = 'temp_book') -> None:
    """
    Import text into database, creating BookLine and LineVariation for each line.
    
    Args:
        text: The full text content
        book_id: Identifier for this book
    """
    if not text or not text.strip():
        return  # Handle empty text gracefully
    
    lines = text.splitlines()
    
    # Prepare batch data
    book_lines_data = []
    line_variations_data = []
    
    for index, line_content in enumerate(lines, start=1):
        book_line_id = str(uuid.uuid4())
        line_variation_id = str(uuid.uuid4())
        
        # BookLine entry
        book_lines_data.append({
            'book_line_id': book_line_id,
            'book_id': book_id,
            'book_line_number': index,
            'original_line_variation_id': line_variation_id,
            'active_line_variation_id': line_variation_id,
        })
        
        # LineVariation entry
        line_variations_data.append({
            'line_variation_id': line_variation_id,
            'book_id': book_id,
            'book_line_id': book_line_id,
            'book_line_number': index,
            'text_content': line_content
        })
    
    # Bulk insert for performance
    with db.atomic():
        # Insert in chunks to avoid memory issues
        for batch in chunked(book_lines_data, 1000):
            BookLine.insert_many(batch).execute()
        
        for batch in chunked(line_variations_data, 1000):
            LineVariation.insert_many(batch).execute()


def find_and_mark_chapters(
    heading_regex: Pattern[str],
    parse_num_func: Callable[[str], Optional[int]],
    is_valid_func: Callable[[str], bool]
) -> None:
    """
    Find chapter headings in the database and mark them.
    Uses peewee ORM to efficiently filter lines containing 'chapter' first.
    
    Args:
        heading_regex: Compiled regex pattern for chapter headings
        parse_num_func: Function to parse chapter numbers
        is_valid_func: Function to validate chapter lines
    """
    # First pass: Use peewee ORM to find all lines containing 'chapter' (case insensitive)
    # This reduces our search space from 600K+ lines to just a few thousand
    potential_chapter_lines = (LineVariation
                              .select(LineVariation, BookLine)
                              .join(BookLine, on=(LineVariation.book_line_id == BookLine.book_line_id))
                              .where(fn.LOWER(LineVariation.text_content).contains('chapter'))
                              .order_by(LineVariation.book_line_number))
    
    # Process these candidates with regex and validation
    validated_chapters = []
    
    for line_var in potential_chapter_lines:
        content = line_var.text_content.strip()
        match = heading_regex.match(content)
        
        if match:
            # Additional validation
            if not is_valid_func(line_var.text_content):
                continue
            
            # Extract chapter number
            num_str = (match.group("num_d") or match.group("num_r") or 
                      match.group("num_w") or match.group("part_d") or 
                      match.group("part_r") or match.group("part_w") or
                      match.group("sec_d") or match.group("hash_d"))
            
            num = parse_num_func(num_str) if num_str else None
            if num is None:
                continue
            
            validated_chapters.append({
                'line_var': line_var,
                'chapter_number': num,
                'content': content,
                'match': match
            })
    
    # Second pass: Apply duplicate detection using peewee queries
    chapter_updates = []
    
    for i, chapter in enumerate(validated_chapters):
        line_var = chapter['line_var']
        num = chapter['chapter_number']
        content = chapter['content']
        match = chapter['match']
        
        # Use peewee to check for duplicates within 4-line window
        is_duplicate = False
        
        # Check previous chapters in our validated list
        for j in range(max(0, i - 1), i):
            prev = validated_chapters[j]
            lines_apart = line_var.book_line_number - prev['line_var'].book_line_number
            
            if lines_apart <= 4:
                # Same text within 4 lines = duplicate
                if content == prev['content']:
                    is_duplicate = True
                    break
                # Same number within 4 lines = multi-part (not duplicate)
                # Will be handled by sub-numbering
        
        if is_duplicate:
            continue
        
        # Extract subtitle for title
        subtitle = (match.group("rest") or "").strip()
        title = f"Chapter {num}{(' – ' + subtitle) if subtitle else ''}"
        
        # Mark this BookLine as a chapter
        chapter_updates.append({
            'book_line_id': line_var.book_line_id,
            'is_chapter_heading': True,
            'chapter_number': num,
            'book_line_title': title
        })
    
    # Bulk update BookLines using peewee
    if chapter_updates:
        with db.atomic():
            # Use bulk update for better performance
            # Process in chunks to avoid query size limits
            for batch in chunked(chapter_updates, 100):
                for update in batch:
                    (BookLine
                     .update(
                         is_chapter_heading=update['is_chapter_heading'],
                         chapter_number=update['chapter_number'],
                         book_line_title=update['book_line_title']
                     )
                     .where(BookLine.book_line_id == update['book_line_id'])
                     .execute())


def get_chapters_with_content() -> Tuple[List[Tuple[str, str]], List[int]]:
    """
    Get all chapters with their content and handle sub-numbering.
    Uses efficient peewee ORM queries.
    
    Returns:
        Tuple of (chapters list with content, chapter number sequence)
    """
    # Get all chapter headings using peewee
    chapters_query = (BookLine
                     .select(BookLine.book_line_number, 
                            BookLine.chapter_number,
                            BookLine.book_line_title)
                     .where(BookLine.is_chapter_heading)
                     .order_by(BookLine.book_line_number))
    
    chapters_info = list(chapters_query.dicts())
    
    if not chapters_info:
        # No chapters found, return all as content
        all_lines = (LineVariation
                    .select()
                    .order_by(LineVariation.book_line_number))
        content = '\n'.join([line.text_content for line in all_lines])
        return [("Content", content.strip())], []
    
    # Count occurrences for sub-numbering using peewee aggregation
    chapter_counts = {}
    count_query = (BookLine
                  .select(BookLine.chapter_number, fn.COUNT(BookLine.chapter_number).alias('count'))
                  .where((BookLine.is_chapter_heading) & 
                         (BookLine.chapter_number.is_null(False)))
                  .group_by(BookLine.chapter_number))
    
    for row in count_query:
        chapter_counts[row.chapter_number] = row.count
    
    # Apply sub-numbering
    part_counters: Dict[int, int] = {}
    final_chapters_info = []
    
    for ch in chapters_info:
        num = ch['chapter_number']
        if chapter_counts.get(num, 1) > 1:
            # Multi-part chapter
            part_counters[num] = part_counters.get(num, 0) + 1
            part_num = part_counters[num]
            
            # Update title with sub-number
            title = ch['book_line_title']
            if ' – ' in title:
                base, subtitle = title.split(' – ', 1)
                new_title = f"Chapter {num}.{part_num}: {subtitle}"
            else:
                new_title = f"Chapter {num}.{part_num}"
            
            ch['book_line_title'] = new_title
        
        final_chapters_info.append(ch)
    
    # Build chapters with content
    chapters = []
    seq = []
    
    # Get total line count using peewee
    total_lines = BookLine.select(fn.MAX(BookLine.book_line_number)).scalar() or 0
    
    # Add front matter if exists
    first_chapter_line = final_chapters_info[0]['book_line_number']
    if first_chapter_line > 1:
        # Get front matter content using peewee
        front_matter_lines = (LineVariation
                            .select(LineVariation.text_content)
                            .where(LineVariation.book_line_number < first_chapter_line)
                            .order_by(LineVariation.book_line_number))
        
        content = '\n'.join([line.text_content for line in front_matter_lines])
        if content.strip():
            chapters.append(("Front Matter", content.strip()))
    
    # Process each chapter
    for i, ch_info in enumerate(final_chapters_info):
        start_line = ch_info['book_line_number']
        end_line = (final_chapters_info[i + 1]['book_line_number'] 
                   if i + 1 < len(final_chapters_info) 
                   else total_lines + 1)
        
        # Get chapter content using peewee (excluding the heading line)
        content_query = (LineVariation
                        .select(LineVariation.text_content)
                        .where(
                            (LineVariation.book_line_number > start_line) &
                            (LineVariation.book_line_number < end_line)
                        )
                        .order_by(LineVariation.book_line_number))
        
        content = '\n'.join([line.text_content for line in content_query])
        chapters.append((ch_info['book_line_title'], content.strip()))
        seq.append(ch_info['chapter_number'])
    
    return chapters, seq