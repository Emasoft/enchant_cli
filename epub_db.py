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
from typing import List, Tuple, Optional, Dict, Any
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
    db.connect()
    db.create_tables([BookLine, LineVariation])


def close_database() -> None:
    """Close database connection"""
    if not db.is_closed():
        db.close()


def import_text_to_db(text: str, book_id: str = 'temp_book') -> None:
    """
    Import text into database, creating BookLine and LineVariation for each line.
    
    Args:
        text: The full text content
        book_id: Identifier for this book
    """
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
    heading_regex: re.Pattern,
    parse_num_func: callable,
    is_valid_func: callable
) -> None:
    """
    Find chapter headings in the database and mark them.
    
    Args:
        heading_regex: Compiled regex pattern for chapter headings
        parse_num_func: Function to parse chapter numbers
        is_valid_func: Function to validate chapter lines
    """
    # Query all LineVariations and check for chapter patterns
    chapter_updates = []
    
    # Use a single query with join for efficiency
    query = (LineVariation
             .select(LineVariation, BookLine)
             .join(BookLine, on=(LineVariation.book_line_id == BookLine.book_line_id))
             .order_by(LineVariation.book_line_number))
    
    # Track for duplicate detection
    last_chapter_line = -10
    last_chapter_num = None
    last_chapter_text = None
    
    for line_var in query:
        content = line_var.text_content.strip()
        match = heading_regex.match(content)
        
        if match:
            # Additional validation
            if 'chapter' in content.lower() and not is_valid_func(line_var.text_content):
                continue
            
            # Extract chapter number
            num_str = (match.group("num_d") or match.group("num_r") or 
                      match.group("num_w") or match.group("part_d") or 
                      match.group("part_r") or match.group("part_w") or
                      match.group("sec_d") or match.group("hash_d"))
            
            num = parse_num_func(num_str) if num_str else None
            if num is None:
                continue
            
            # Smart duplicate detection
            lines_since_last = line_var.book_line_number - last_chapter_line
            
            # Skip if same text within 4 lines
            if lines_since_last <= 4 and content == last_chapter_text:
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
            
            # Update tracking
            last_chapter_line = line_var.book_line_number
            last_chapter_num = num
            last_chapter_text = content
    
    # Bulk update BookLines
    if chapter_updates:
        with db.atomic():
            for update in chapter_updates:
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
    
    Returns:
        Tuple of (chapters list with content, chapter number sequence)
    """
    # Get all chapter headings
    chapter_query = (BookLine
                    .select()
                    .where(BookLine.is_chapter_heading == True)
                    .order_by(BookLine.book_line_number))
    
    chapters_info = []
    for chapter in chapter_query:
        chapters_info.append({
            'line_number': chapter.book_line_number,
            'chapter_number': chapter.chapter_number,
            'title': chapter.book_line_title
        })
    
    # Count occurrences for sub-numbering
    chapter_counts = {}
    for ch in chapters_info:
        num = ch['chapter_number']
        chapter_counts[num] = chapter_counts.get(num, 0) + 1
    
    # Apply sub-numbering
    part_counters = {}
    final_chapters_info = []
    
    for ch in chapters_info:
        num = ch['chapter_number']
        if chapter_counts.get(num, 1) > 1:
            # Multi-part chapter
            part_counters[num] = part_counters.get(num, 0) + 1
            part_num = part_counters[num]
            
            # Update title with sub-number
            title = ch['title']
            if ' – ' in title:
                base, subtitle = title.split(' – ', 1)
                new_title = f"Chapter {num}.{part_num}: {subtitle}"
            else:
                new_title = f"Chapter {num}.{part_num}"
            
            ch['title'] = new_title
        
        final_chapters_info.append(ch)
    
    # Now build chapters with content
    chapters = []
    seq = []
    
    # Get total line count
    total_lines = BookLine.select(fn.MAX(BookLine.book_line_number)).scalar()
    
    # Add front matter if exists
    if final_chapters_info and final_chapters_info[0]['line_number'] > 1:
        # Get front matter content
        front_matter_lines = (LineVariation
                            .select()
                            .where(LineVariation.book_line_number < final_chapters_info[0]['line_number'])
                            .order_by(LineVariation.book_line_number))
        
        content = '\n'.join([line.text_content for line in front_matter_lines])
        if content.strip():
            chapters.append(("Front Matter", content.strip()))
    
    # Process each chapter
    for i, ch_info in enumerate(final_chapters_info):
        start_line = ch_info['line_number']
        end_line = final_chapters_info[i + 1]['line_number'] if i + 1 < len(final_chapters_info) else total_lines + 1
        
        # Get chapter content (excluding the heading line itself)
        content_lines = (LineVariation
                        .select()
                        .where(
                            (LineVariation.book_line_number > start_line) &
                            (LineVariation.book_line_number < end_line)
                        )
                        .order_by(LineVariation.book_line_number))
        
        content = '\n'.join([line.text_content for line in content_lines])
        chapters.append((ch_info['title'], content.strip()))
        seq.append(ch_info['chapter_number'])
    
    return chapters, seq